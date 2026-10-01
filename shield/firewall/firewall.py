"""The action firewall: the single ToolHook that combines every AgentShield layer.

Incoming content (after_result) is labelled, scored by the detectors, fused into one risk, and
then allowed, sanitized, or withheld. Proposed actions (before_call) are checked against the
canary tripwires, the taint policy, and the per-task permissions, and sensitive or suspicious
actions are sent for human approval. Unanswered approvals are denied after a timeout.
"""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agents.config import REPO_ROOT
from agents.hooks import Decision, ToolCall, ToolResult
from shield.canary import CanaryVault
from shield.detectors import Context, RuleDetector
from shield.detectors.base import Detector
from shield.firewall.policy import Policy, Profile
from shield.firewall.sanitize import sanitize
from shield.scoring import FEATURES, RiskFuser
from shield.taint import TaintTracker, TaintVerdict

_SINK_TOOLS = {"send_email", "http_post", "browse_web", "write_file"}


def _top(signals: dict[str, float]) -> str:
    return max(signals, key=lambda name: signals[name]) if signals and max(signals.values()) > 0 else ""


@dataclass
class ApprovalRequest:
    call: ToolCall
    reason: str


# An approver decides a human-in-the-loop action. The default denies everything (fail-safe);
# a demo or dashboard supplies one that actually asks. Auto-approve is used only to measure
# utility, where it models the user approving their own legitimate request.
Approver = Callable[[ApprovalRequest], bool]


def deny_all(request: ApprovalRequest) -> bool:
    return False


def auto_approve(request: ApprovalRequest) -> bool:
    return True


@dataclass
class Firewall:
    vault: CanaryVault
    taint: TaintTracker
    fuser: RiskFuser
    profile: Profile
    sanitize_at: float = 0.5
    block_content_at: float = 0.85
    approver: Approver = deny_all
    approval_timeout: float = 30.0
    detectors: list[Detector] = field(default_factory=lambda: [RuleDetector()])
    context: Context = field(default_factory=Context)
    events: list[dict[str, Any]] = field(default_factory=list)
    # Optional callback receiving each decision, e.g. to persist to the API store for the dashboard.
    sink: Callable[[dict[str, Any]], None] | None = None
    incident_id: str | None = None

    def begin(self, task: str) -> None:
        self.context.user_task = task

    def _emit(self, event: dict[str, Any]) -> None:
        if self.sink is not None:
            self.sink({"incident_id": self.incident_id, **event})

    # --- incoming content -------------------------------------------------
    def after_result(self, result: ToolResult) -> ToolResult:
        origin = self.taint.observe(result.source, result.content)
        result.annotations["origin"] = str(origin)

        risk, per_detector = self._score_content(result.content)
        result.annotations["risk"] = round(risk, 3)
        result.annotations["detectors"] = per_detector

        if risk >= self.block_content_at:
            result.annotations["action"] = "blocked"
            result.content = "[AgentShield withheld this content: high prompt-injection risk]"
        elif risk >= self.sanitize_at:
            wrapped, removed = sanitize(result.content, self._sentence_flagged)
            result.content = wrapped
            result.annotations["action"] = "sanitized"
            result.annotations["removed"] = removed
        else:
            result.annotations["action"] = "allowed"
        self._emit({
            "type": "scan", "source": result.source, "risk": result.annotations["risk"],
            "outcome": result.annotations["action"], "layer": _top(per_detector),
            "reason": f"content from {result.source}", "detail": {"origin": result.annotations["origin"]},
        })
        return result

    def _score_content(self, content: str) -> tuple[float, dict[str, float]]:
        from shield.preprocess import preprocess_text

        best = 0.0
        best_detail: dict[str, float] = {}
        for chunk in preprocess_text(content, "external") or [None]:
            signals = {name: 0.0 for name in FEATURES}
            if chunk is not None:
                for detector in self.detectors:
                    signal = detector.score(chunk, self.context)
                    key = {"rules": "rules", "classifier": "classifier", "intent": "intent"}.get(detector.name)
                    if key:
                        signals[key] = signal.score
            risk = self.fuser.fuse(signals)
            if risk >= best:
                best, best_detail = risk, signals
        return best, best_detail

    def _sentence_flagged(self, sentence: str) -> bool:
        from shield.preprocess import analyze_text

        chunk = analyze_text(sentence, "external")
        return any(detector.score(chunk, self.context).score >= self.sanitize_at for detector in self.detectors)

    # --- outgoing actions -------------------------------------------------
    def before_call(self, call: ToolCall) -> Decision:
        if call.tool not in self.profile.allow_tools:
            return self._record(call, "block", f"tool {call.tool!r} is not permitted for this task")

        if call.tool in _SINK_TOOLS:
            hits = self.vault.scan(" ".join(str(value) for value in call.args.values()))
            if hits:
                where = ", ".join(sorted({hit.placement.locator for hit in hits}))
                trigger = self.taint.state.external_sources[-1:] or ["unknown source"]
                return self._record(call, "block", f"canary leak from {where}; likely triggered by {trigger[0]}")

        taint_decision = self.taint.check(call)
        if taint_decision.verdict is TaintVerdict.BLOCK:
            return self._record(call, "block", taint_decision.reason, leaked=taint_decision.leaked_values)

        needs_approval = taint_decision.verdict is TaintVerdict.APPROVAL or call.tool in self.profile.always_approve
        if needs_approval:
            reason = taint_decision.reason if taint_decision.verdict is TaintVerdict.APPROVAL else "sensitive action"
            approved = self._ask(ApprovalRequest(call, reason))
            verdict = "approved" if approved else "denied"
            return self._record(call, "allow" if approved else "block", f"{reason}: {verdict} by human review")

        return self._record(call, "allow", "no canary, taint, or policy concern")

    def _ask(self, request: ApprovalRequest) -> bool:
        """Call the approver with a hard timeout; any timeout or error denies (fail-safe)."""
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                return bool(pool.submit(self.approver, request).result(timeout=self.approval_timeout))
        except (FutureTimeout, Exception):  # noqa: BLE001 - deny on anything unexpected
            return False

    def _record(self, call: ToolCall, outcome: str, reason: str, leaked: list[str] | None = None) -> Decision:
        event = {"type": "action", "tool": call.tool, "outcome": outcome, "reason": reason, "leaked": leaked or []}
        self.events.append(event)
        self._emit(event)
        return Decision.allow(reason) if outcome == "allow" else Decision.block(reason)


def build_firewall(
    sandbox,
    user_task: str = "",
    profile: str = "default",
    detectors: list[Detector] | None = None,
    approver: Approver = deny_all,
    policy: Policy | None = None,
    fuser: RiskFuser | None = None,
) -> tuple[Firewall, str]:
    """Wire a firewall to a sandbox. Returns (firewall, system_prompt_suffix)."""
    policy = policy or Policy.load()
    vault = CanaryVault.for_session()
    vault.seed_sandbox(sandbox)
    chosen = policy.profile(profile)
    fuser = fuser or RiskFuser.load(REPO_ROOT / "models" / "fusion.json")

    firewall = Firewall(
        vault=vault,
        taint=TaintTracker(sandbox.secrets, internal_domains=set(chosen.internal_domains)),
        fuser=fuser,
        profile=chosen,
        sanitize_at=policy.thresholds.sanitize,
        block_content_at=policy.thresholds.block_content,
        approver=approver,
        approval_timeout=policy.approval_timeout_seconds,
        detectors=detectors or [RuleDetector()],
        context=Context(user_task=user_task),
    )
    return firewall, vault.prompt_line

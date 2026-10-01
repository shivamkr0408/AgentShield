"""Origin labelling and taint tracking.

Every piece of data the agent reads is labelled by origin, and the tracker remembers which
labels have entered the session's context. The policy it enforces is the one from the plan:
PRIVATE data heading to an EXTERNAL destination, once EXTERNAL content has been read, is the
dangerous combination and is blocked or sent for human approval.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from urllib.parse import urlsplit

from agents.hooks import ToolCall


class Origin(StrEnum):
    USER = "USER"          # the user's own instruction
    PRIVATE = "PRIVATE"    # the user's sensitive data (secrets, private files)
    EXTERNAL = "EXTERNAL"  # untrusted, attacker-reachable content (web, email, files)


class TaintVerdict(StrEnum):
    ALLOW = "allow"
    APPROVAL = "approval"  # context looks dangerous; defer to a human
    BLOCK = "block"        # a private value is literally leaving the boundary


def label_of(source: str, content: str, secrets: list[str]) -> Origin:
    """Classify a tool result's origin. A planted secret anywhere makes it PRIVATE."""
    if any(secret and secret in content for secret in secrets):
        return Origin.PRIVATE
    if source.startswith("file:private/"):
        return Origin.PRIVATE
    # Web, email, and ordinary files are all attacker-reachable in this threat model.
    if source.split(":", 1)[0] in {"web", "http", "inbox"} or source.startswith("file:"):
        return Origin.EXTERNAL
    return Origin.EXTERNAL  # unknown provenance is treated as untrusted


# Tool arguments that send data out of the sandbox, and the fields that carry a destination.
_OUTBOUND = {
    "send_email": ("to",),
    "http_post": ("url",),
    "browse_web": ("url",),
}


def _host(value: str) -> str:
    value = value if "://" in value else f"http://{value}"
    return (urlsplit(value).hostname or "").lower()


def is_external_destination(call: ToolCall, internal_domains: set[str]) -> bool:
    fields = _OUTBOUND.get(call.tool)
    if not fields:
        return False
    for field_name in fields:
        value = str(call.args.get(field_name, ""))
        destination = value.split("@")[-1] if "@" in value else _host(value)
        if destination and not any(destination == domain or destination.endswith("." + domain) for domain in internal_domains):
            return True
    return False


@dataclass
class TaintState:
    labels_seen: set[Origin] = field(default_factory=set)
    private_sources: list[str] = field(default_factory=list)
    external_sources: list[str] = field(default_factory=list)
    private_values: list[str] = field(default_factory=list)  # concrete PRIVATE strings read


@dataclass
class TaintDecision:
    verdict: TaintVerdict
    reason: str
    labels_in_context: list[Origin] = field(default_factory=list)
    leaked_values: list[str] = field(default_factory=list)


class TaintTracker:
    def __init__(self, secrets: list[str], internal_domains: set[str] | None = None) -> None:
        self.secrets = [s for s in secrets if s]
        self.internal_domains = internal_domains or {"acme.test"}
        self.state = TaintState(labels_seen={Origin.USER})

    def observe(self, source: str, content: str) -> Origin:
        """Record an incoming tool result and return its origin label."""
        origin = label_of(source, content, self.secrets)
        self.state.labels_seen.add(origin)
        if origin is Origin.PRIVATE:
            self.state.private_sources.append(source)
            self.state.private_values.extend(secret for secret in self.secrets if secret in content)
        elif origin is Origin.EXTERNAL:
            self.state.external_sources.append(source)
        return origin

    def check(self, call: ToolCall) -> TaintDecision:
        """Apply the PRIVATE -> EXTERNAL policy to a proposed action."""
        labels = sorted(self.state.labels_seen)
        if not is_external_destination(call, self.internal_domains):
            return TaintDecision(TaintVerdict.ALLOW, "destination is internal", labels)

        args_text = " ".join(str(value) for value in call.args.values())
        leaked = [value for value in self.state.private_values if value in args_text]
        if leaked:
            return TaintDecision(
                TaintVerdict.BLOCK,
                "a PRIVATE value is being sent to an external destination",
                labels,
                leaked_values=leaked,
            )
        if Origin.PRIVATE in self.state.labels_seen and Origin.EXTERNAL in self.state.labels_seen:
            return TaintDecision(
                TaintVerdict.APPROVAL,
                "external action after PRIVATE and EXTERNAL data were both read",
                labels,
            )
        return TaintDecision(TaintVerdict.ALLOW, "no PRIVATE+EXTERNAL combination in context", labels)

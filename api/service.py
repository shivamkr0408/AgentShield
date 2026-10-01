"""The shield service that backs the API: scanning content, checking actions, and keeping
per-incident taint and canary state. It records every decision to the store and returns the
event so the route can broadcast it.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from agents.hooks import Kind, Risk, ToolCall
from api.db import Approval, Event, Incident, PolicyRow, ResultsRow, _now
from shield.canary import CanaryVault
from shield.detectors import ClassifierDetector, Context, RuleDetector
from shield.detectors.base import Detector
from shield.firewall.sanitize import sanitize
from shield.preprocess import preprocess_text
from shield.scoring import FEATURES, RiskFuser
from shield.taint import TaintTracker, TaintVerdict

_DEFAULT_THRESHOLDS = {"sanitize": 0.5, "block_content": 0.85}
_DEFAULT_LAYERS = {"rules": True, "classifier": True, "intent": True, "canary": True, "taint": True}
_ACTION_RISK = {"send_email": Risk.HIGH, "http_post": Risk.HIGH, "transfer_money": Risk.HIGH, "write_file": Risk.MEDIUM, "browse_web": Risk.MEDIUM}
_ALWAYS_APPROVE = {"transfer_money"}


class SessionState:
    def __init__(self, secrets: list[str]) -> None:
        self.vault = CanaryVault.for_session()
        for secret in secrets:
            self.vault.register(secret, self.vault.registry.get(secret, _secret_placement(secret)))
        self.taint = TaintTracker(secrets)


def _secret_placement(secret: str):
    from shield.canary import Placement

    return Placement("known_secret", "provided")


class ShieldService:
    def __init__(self, sessions: sessionmaker[Session], judge=None) -> None:
        self._db = sessions
        self._states: dict[str, SessionState] = {}
        self.fuser = RiskFuser()
        self._rules = RuleDetector()
        self._classifier = ClassifierDetector()
        self._intent = None
        if judge is not None:
            from shield.detectors import IntentDetector

            self._intent = IntentDetector(judge=judge)
        self._ensure_policy()

    # --- policy -----------------------------------------------------------
    def _ensure_policy(self) -> None:
        with self._db.begin() as session:
            if session.get(PolicyRow, 1) is None:
                session.add(PolicyRow(id=1, thresholds=dict(_DEFAULT_THRESHOLDS), layers=dict(_DEFAULT_LAYERS)))

    def get_policy(self) -> dict[str, Any]:
        with self._db() as session:
            return session.get(PolicyRow, 1).as_dict()

    def update_policy(self, thresholds: dict | None, layers: dict | None, timeout: float | None) -> dict[str, Any]:
        with self._db.begin() as session:
            row = session.get(PolicyRow, 1)
            if thresholds:
                row.thresholds = {**row.thresholds, **thresholds}
            if layers:
                row.layers = {**row.layers, **layers}
            if timeout is not None:
                row.approval_timeout_seconds = timeout
            return row.as_dict()

    def _active_detectors(self) -> list[Detector]:
        layers = self.get_policy()["layers"]
        detectors: list[Detector] = []
        if layers.get("rules", True):
            detectors.append(self._rules)
        if layers.get("classifier", True) and self._classifier.available:
            detectors.append(self._classifier)
        if layers.get("intent", True) and self._intent is not None:
            detectors.append(self._intent)
        return detectors

    # --- incidents --------------------------------------------------------
    def create_incident(self, task: str = "", secrets: list[str] | None = None) -> dict[str, Any]:
        incident_id = "inc-" + uuid.uuid4().hex[:12]
        self._states[incident_id] = SessionState(secrets or [])
        with self._db.begin() as session:
            session.add(Incident(id=incident_id, task=task))
        return {"incident_id": incident_id, "canary_token": self._states[incident_id].vault.session_token}

    def _state(self, incident_id: str | None) -> SessionState:
        if incident_id and incident_id in self._states:
            return self._states[incident_id]
        return SessionState([])

    # --- scanning content -------------------------------------------------
    def scan(self, content: str, source: str, incident_id: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
        detectors = self._active_detectors()
        context = Context(user_task="")
        thresholds = self.get_policy()["thresholds"]

        best_risk, best_layers, chunk_reports = 0.0, {}, []
        for chunk in preprocess_text(content, source) or []:
            signals = {name: 0.0 for name in FEATURES}
            for detector in detectors:
                if detector.name in signals:
                    signals[detector.name] = round(detector.score(chunk, context).score, 4)
            risk = self.fuser.fuse(signals)
            chunk_reports.append({"text": chunk.text[:400], "risk": round(risk, 4), "flags": _flags(chunk), "signals": signals})
            if risk >= best_risk:
                best_risk, best_layers = risk, signals

        outcome = "allow"
        sanitized = None
        if best_risk >= thresholds.get("block_content", 0.85):
            outcome = "block"
        elif best_risk >= thresholds.get("sanitize", 0.5):
            outcome = "sanitize"
            sanitized, _ = sanitize(content, lambda s: self._rules.score(_as_chunk(s, source), context).score >= thresholds.get("sanitize", 0.5))

        if incident_id and incident_id in self._states:
            self._states[incident_id].taint.observe(source, content)

        verdict = {
            "risk": round(best_risk, 4),
            "label": "attack" if best_risk >= thresholds.get("sanitize", 0.5) else "benign",
            "outcome": outcome,
            "layers": best_layers,
            "chunks": chunk_reports,
            "sanitized": sanitized,
        }
        event = self._record(
            incident_id, "scan", outcome=outcome, source=source, risk=round(best_risk, 4),
            layer=_top_layer(best_layers), reason=f"content scan: {outcome}", detail={"layers": best_layers},
        )
        return verdict, event

    # --- checking actions -------------------------------------------------
    def check_action(self, tool: str, args: dict[str, Any], incident_id: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
        state = self._state(incident_id)
        layers = self.get_policy()["layers"]
        call = ToolCall(call_id=uuid.uuid4().hex[:8], tool=tool, args=args, kind=Kind.ACTION, risk=_ACTION_RISK.get(tool, Risk.LOW))

        outcome, layer, reason, approval_id = "allow", "", "no concern", None

        if layers.get("canary", True):
            hits = state.vault.scan(" ".join(str(value) for value in args.values()))
            if hits:
                where = ", ".join(sorted({hit.placement.locator for hit in hits}))
                outcome, layer, reason = "block", "canary", f"canary leak from {where}"

        if outcome == "allow" and layers.get("taint", True):
            decision = state.taint.check(call)
            if decision.verdict is TaintVerdict.BLOCK:
                outcome, layer, reason = "block", "taint", decision.reason
            elif decision.verdict is TaintVerdict.APPROVAL or tool in _ALWAYS_APPROVE:
                outcome, layer, reason = "approval", "taint", decision.reason if decision.verdict is TaintVerdict.APPROVAL else "sensitive action"
        elif outcome == "allow" and tool in _ALWAYS_APPROVE:
            outcome, layer, reason = "approval", "policy", "sensitive action"

        if outcome == "approval":
            approval_id = "apr-" + uuid.uuid4().hex[:12]
            with self._db.begin() as session:
                session.add(Approval(id=approval_id, incident_id=incident_id, tool=tool, args=args, reason=reason))

        result = {"outcome": outcome, "reason": reason, "layer": layer, "approval_id": approval_id}
        event = self._record(incident_id, "action", outcome=outcome, tool=tool, layer=layer, reason=reason, detail={"args": _safe(args)})
        return result, event

    # --- approvals --------------------------------------------------------
    def list_approvals(self, status: str | None = None) -> list[dict[str, Any]]:
        with self._db() as session:
            query = select(Approval).order_by(Approval.created_at.desc())
            if status:
                query = query.where(Approval.status == status)
            return [row.as_dict() for row in session.scalars(query)]

    def get_approval(self, approval_id: str) -> dict[str, Any] | None:
        with self._db() as session:
            row = session.get(Approval, approval_id)
            return row.as_dict() if row else None

    def resolve_approval(self, approval_id: str, approve: bool) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        with self._db.begin() as session:
            row = session.get(Approval, approval_id)
            if row is None or row.status != "pending":
                return (row.as_dict() if row else None), None
            row.status = "approved" if approve else "denied"
            row.resolved_at = _now()
            resolved = row.as_dict()
        event = self._record(
            resolved["incident_id"], "approval", outcome=resolved["status"], tool=resolved["tool"],
            layer="approval", reason=f"approval {resolved['status']}",
        )
        return resolved, event

    # --- history and stats -----------------------------------------------
    def list_events(self, limit: int = 100, incident_id: str | None = None) -> list[dict[str, Any]]:
        with self._db() as session:
            query = select(Event).order_by(Event.id.desc()).limit(limit)
            if incident_id:
                query = select(Event).where(Event.incident_id == incident_id).order_by(Event.id)
            return [row.as_dict() for row in session.scalars(query)]

    def list_incidents(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._db() as session:
            rows = session.scalars(select(Incident).order_by(Incident.created_at.desc()).limit(limit))
            return [row.as_dict() for row in rows]

    def get_incident(self, incident_id: str) -> dict[str, Any] | None:
        with self._db() as session:
            incident = session.get(Incident, incident_id)
            if incident is None:
                return None
            events = [row.as_dict() for row in session.scalars(
                select(Event).where(Event.incident_id == incident_id).order_by(Event.id))]
            return {**incident.as_dict(), "events": events}

    def stats(self) -> dict[str, Any]:
        with self._db() as session:
            def count(*conditions):
                query = select(func.count()).select_from(Event)
                for condition in conditions:
                    query = query.where(condition)
                return session.scalar(query) or 0

            by_layer = dict(session.execute(
                select(Event.layer, func.count()).where(Event.outcome == "block").group_by(Event.layer)).all())
            return {
                "events": count(),
                "blocked": count(Event.outcome == "block"),
                "sanitized": count(Event.outcome == "sanitize"),
                "incidents": session.scalar(select(func.count()).select_from(Incident)) or 0,
                "pending_approvals": session.scalar(
                    select(func.count()).select_from(Approval).where(Approval.status == "pending")) or 0,
                "blocks_by_layer": {key or "?": value for key, value in by_layer.items()},
            }

    # --- benchmark results ------------------------------------------------
    def set_results(self, data: dict[str, Any]) -> dict[str, Any]:
        with self._db.begin() as session:
            row = session.get(ResultsRow, 1)
            if row is None:
                session.add(ResultsRow(id=1, data=data, updated_at=_now()))
            else:
                row.data = data
                row.updated_at = _now()
        return data

    def get_results(self) -> dict[str, Any]:
        with self._db() as session:
            row = session.get(ResultsRow, 1)
            return row.data if row is not None and row.data else {}

    # --- recording --------------------------------------------------------
    def _record(self, incident_id: str | None, type_: str, **fields: Any) -> dict[str, Any]:
        with self._db.begin() as session:
            event = Event(incident_id=incident_id, type=type_, **fields)
            session.add(event)
            session.flush()
            return event.as_dict()


def _flags(chunk) -> list[str]:
    names = {"hidden": chunk.hidden, "encoded": chunk.encoded, "homoglyph": chunk.homoglyph, "invisible": chunk.invisible}
    return [name for name, on in names.items() if on]


def _as_chunk(text: str, source: str):
    from shield.preprocess import analyze_text

    return analyze_text(text, source)


def _top_layer(signals: dict[str, float]) -> str:
    return max(signals, key=lambda name: signals[name]) if signals and max(signals.values()) > 0 else ""


def _safe(args: dict[str, Any]) -> dict[str, Any]:
    return {key: (value[:120] if isinstance(value, str) else value) for key, value in args.items()}

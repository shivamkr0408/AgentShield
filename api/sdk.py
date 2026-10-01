"""AgentShield SDK: wrap an agent run so every tool call passes through the shield.

    from api.sdk import AgentShield
    protected = AgentShield.wrap(run_agent)          # default policy
    protected("Summarize the reviews.", sandbox, model)

The firewall is built from the sandbox (so canaries are seeded and secrets are tracked) and
injected as the agent's tool hook. Pass ``store_url`` to also persist decisions where the API
and dashboard can read them.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from agents.agent import AgentRun, run_agent
from shield.detectors.base import Detector
from shield.firewall import Approver, Firewall, build_firewall, deny_all
from shield.firewall.policy import Policy


@dataclass
class AgentShield:
    policy: Policy
    detectors: list[Detector] | None = None
    approver: Approver = deny_all
    profile: str = "default"
    sink: Callable[[dict[str, Any]], None] | None = None

    @classmethod
    def create(
        cls,
        policy: Policy | None = None,
        approver: Approver = deny_all,
        profile: str = "default",
        store_url: str | None = None,
    ) -> AgentShield:
        sink = _store_sink(store_url) if store_url else None
        return cls(policy=policy or Policy.load(), approver=approver, profile=profile, sink=sink)

    def instrument(self, sandbox, task: str = "") -> tuple[Firewall, str]:
        firewall, suffix = build_firewall(
            sandbox, user_task=task, profile=self.profile, detectors=self.detectors,
            approver=self.approver, policy=self.policy,
        )
        firewall.sink = self.sink
        return firewall, suffix

    def run(self, task: str, sandbox, model, **kwargs: Any) -> AgentRun:
        firewall, suffix = self.instrument(sandbox, task)
        return run_agent(task, sandbox, model, hook=firewall, system_suffix=suffix, **kwargs)

    @classmethod
    def wrap(cls, run_fn: Callable = run_agent, **create_kwargs: Any) -> Callable:
        """Return a drop-in replacement for run_agent that enforces the shield."""
        shield = cls.create(**create_kwargs)

        def protected(task: str, sandbox, model, **kwargs: Any) -> AgentRun:
            firewall, suffix = shield.instrument(sandbox, task)
            return run_fn(task, sandbox, model, hook=firewall, system_suffix=suffix, **kwargs)

        return protected


def _store_sink(store_url: str) -> Callable[[dict[str, Any]], None]:
    """A sink that persists firewall decisions to the API's store for the dashboard to read."""
    from api.db import Event, make_sessionmaker

    sessions = make_sessionmaker(store_url)

    def sink(event: dict[str, Any]) -> None:
        with sessions.begin() as session:
            session.add(Event(
                incident_id=event.get("incident_id"),
                type=event.get("type", "action"),
                outcome=event.get("outcome", ""),
                tool=event.get("tool", ""),
                source=event.get("source", ""),
                risk=float(event.get("risk", 0.0) or 0.0),
                layer=event.get("layer", ""),
                reason=event.get("reason", ""),
                detail=event.get("detail", {}),
            ))

    return sink

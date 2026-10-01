"""The single interception point between the agent and its tools.

Every tool call the model proposes reaches ``ToolHook.before_call`` before it runs, and
every piece of tool output reaches ``ToolHook.after_result`` before the model sees it.
AgentShield's defense layers plug in by implementing ``ToolHook``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol


class Kind(StrEnum):
    READ = "read"
    ACTION = "action"


class Risk(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class ToolCall:
    call_id: str
    tool: str
    args: dict[str, Any]
    kind: Kind
    risk: Risk


@dataclass
class ToolResult:
    call: ToolCall
    content: str
    # Where the content came from, e.g. "inbox:e-104", "web:http://acme.test/team" or "file:docs/a.md".
    source: str
    # Tool output is attacker-reachable by default; later layers may refine this.
    trusted: bool = False
    annotations: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str = ""

    @classmethod
    def allow(cls, reason: str = "") -> Decision:
        return cls(True, reason)

    @classmethod
    def block(cls, reason: str) -> Decision:
        return cls(False, reason)


class ToolHook(Protocol):
    def before_call(self, call: ToolCall) -> Decision: ...

    def after_result(self, result: ToolResult) -> ToolResult: ...


class PassThroughHook:
    """No defense: the undefended baseline."""

    def before_call(self, call: ToolCall) -> Decision:
        return Decision.allow()

    def after_result(self, result: ToolResult) -> ToolResult:
        return result

"""Structured event log for one agent run.

The same events are saved as JSONL for evaluation and will later be streamed to the dashboard.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

Listener = Callable[[dict[str, Any]], None]


class Trace:
    def __init__(self, listeners: list[Listener] | None = None) -> None:
        self.events: list[dict[str, Any]] = []
        self._listeners = list(listeners or [])

    def subscribe(self, listener: Listener) -> None:
        self._listeners.append(listener)

    def emit(self, event_type: str, **data: Any) -> dict[str, Any]:
        event = {"seq": len(self.events), "ts": round(time.time(), 3), "type": event_type, **data}
        self.events.append(event)
        for listener in self._listeners:
            listener(event)
        return event

    def of_type(self, event_type: str) -> list[dict[str, Any]]:
        return [event for event in self.events if event["type"] == event_type]

    def dump(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            for event in self.events:
                handle.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")


def _clip(text: str, limit: int = 160) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else f"{text[: limit - 3]}..."


def console_printer(event: dict[str, Any]) -> None:
    """Prints a one-line summary of each event, for live demos."""
    kind = event["type"]
    if kind == "task":
        print(f"\nTASK  {event['task']}")
    elif kind == "injection":
        print(f"INJECTED  scenario {event['scenario']} into {event['slot']['kind']}:{event['slot']['target']}")
    elif kind == "llm_response" and event["content"]:
        print(f"  model   {_clip(event['content'])}")
    elif kind == "tool_call":
        print(f"  call    {event['tool']}({_clip(event['args'], 120)})  [{event['kind']}, risk={event['risk']}]")
    elif kind == "decision" and not event["allowed"]:
        print(f"  BLOCKED {event['reason']}")
    elif kind == "tool_result":
        print(f"  result  <{event['source']}> {_clip(event['content'], 120)}")
    elif kind == "tool_error":
        print(f"  error   {event['tool']}: {event['error']}")
    elif kind == "final":
        print(f"ANSWER ({event['status']})  {event['answer']}")
    elif kind == "run_error":
        print(f"RUN ERROR  {event['error']}")

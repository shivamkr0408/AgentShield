"""Loading and validating benign tasks and injection scenarios."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agents.config import REPO_ROOT
from agents.sandbox import InjectionSlot
from eval.checks import CHECKS

TASKS_FILE = REPO_ROOT / "data" / "tasks" / "benign_tasks.json"


@dataclass(frozen=True)
class Task:
    id: str
    prompt: str
    checks: list[dict[str, Any]]
    category: str = ""


@dataclass(frozen=True)
class InjectionScenario:
    """A benign task run in a world where one untrusted source carries an injected payload."""

    id: str
    task_id: str
    slot: InjectionSlot
    payload: str
    # Checks that pass when the attacker achieved their goal.
    goal: list[dict[str, Any]]
    labels: dict[str, Any] = field(default_factory=dict)


def _validate_checks(owner: str, checks: list[dict[str, Any]]) -> None:
    if not checks:
        raise ValueError(f"{owner} has no checks")
    for check in checks:
        if check.get("type") not in CHECKS:
            raise ValueError(f"{owner} uses unknown check type {check.get('type')!r}")


def load_tasks(path: Path = TASKS_FILE) -> dict[str, Task]:
    tasks: dict[str, Task] = {}
    for raw in json.loads(path.read_text(encoding="utf-8")):
        task = Task(id=raw["id"], prompt=raw["prompt"], checks=raw["checks"], category=raw.get("category", ""))
        _validate_checks(f"Task {task.id}", task.checks)
        if task.id in tasks:
            raise ValueError(f"Duplicate task id {task.id}")
        tasks[task.id] = task
    return tasks


def load_scenarios(path: Path, tasks: dict[str, Task]) -> dict[str, InjectionScenario]:
    """Load scenarios from JSON. The file format is documented in data/attacks/README.md."""
    scenarios: dict[str, InjectionScenario] = {}
    reserved = {"id", "task", "slot", "payload", "goal"}
    for raw in json.loads(path.read_text(encoding="utf-8")):
        scenario = InjectionScenario(
            id=raw["id"],
            task_id=raw["task"],
            slot=InjectionSlot.from_dict(raw["slot"]),
            payload=raw["payload"],
            goal=raw["goal"],
            labels={key: value for key, value in raw.items() if key not in reserved},
        )
        if scenario.task_id not in tasks:
            raise ValueError(f"Scenario {scenario.id} refers to unknown task {scenario.task_id}")
        _validate_checks(f"Scenario {scenario.id}", scenario.goal)
        if scenario.id in scenarios:
            raise ValueError(f"Duplicate scenario id {scenario.id}")
        scenarios[scenario.id] = scenario
    return scenarios

"""Runs tasks and injection scenarios in fresh sandboxes and records the results."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from langchain_core.language_models import BaseChatModel

from agents.agent import run_agent
from agents.hooks import ToolHook
from agents.sandbox import Sandbox
from agents.trace import Listener, Trace
from eval.checks import evaluate, leaked_secrets
from eval.scenarios import InjectionScenario, Task


@dataclass
class CaseResult:
    case_id: str
    task_id: str
    status: str
    llm_calls: int
    task_success: bool
    task_checks: list[dict[str, Any]]
    final_answer: str
    leaked_secrets: list[str]
    outbound: list[dict[str, str]]
    attack_success: bool | None = None
    goal_checks: list[dict[str, Any]] = field(default_factory=list)
    labels: dict[str, Any] = field(default_factory=dict)


def run_case(
    task: Task,
    model: BaseChatModel,
    scenario: InjectionScenario | None = None,
    hook: ToolHook | None = None,
    max_steps: int | None = None,
    trace_path: Path | None = None,
    listeners: list[Listener] | None = None,
    defense: str = "none",
    approver: str = "deny",
) -> CaseResult:
    trace = Trace(listeners)
    with Sandbox() as sandbox:
        if scenario is not None:
            sandbox.inject(scenario.slot, scenario.payload)
            trace.emit("injection", scenario=scenario.id, slot=asdict(scenario.slot), labels=scenario.labels)

        system_suffix = ""
        if defense == "full":
            # Built after injection so canaries are seeded into the final file state.
            from shield.firewall import auto_approve, build_firewall, deny_all

            hook, system_suffix = build_firewall(
                sandbox, user_task=task.prompt, approver=auto_approve if approver == "approve" else deny_all
            )

        run = run_agent(task.prompt, sandbox, model, hook=hook, trace=trace, max_steps=max_steps, system_suffix=system_suffix)
        task_success, task_checks = evaluate(task.checks, run, sandbox)
        result = CaseResult(
            case_id=scenario.id if scenario else task.id,
            task_id=task.id,
            status=run.status,
            llm_calls=run.llm_calls,
            task_success=task_success,
            task_checks=task_checks,
            final_answer=run.final_answer,
            leaked_secrets=leaked_secrets(sandbox),
            outbound=sandbox.outbound(),
        )
        if scenario is not None:
            result.attack_success, result.goal_checks = evaluate(scenario.goal, run, sandbox)
            result.labels = scenario.labels

    trace.emit("result", **asdict(result))
    if trace_path is not None:
        trace.dump(trace_path)
    return result


def summarize(results: list[CaseResult]) -> dict[str, Any]:
    total = len(results)
    summary: dict[str, Any] = {
        "cases": total,
        "task_success_rate": sum(result.task_success for result in results) / total if total else 0.0,
        "runs_with_secret_leak": sum(bool(result.leaked_secrets) for result in results),
        "errors": sum(result.status == "error" for result in results),
        "step_limit": sum(result.status == "step_limit" for result in results),
    }
    attacked = [result for result in results if result.attack_success is not None]
    if attacked:
        summary["attack_success_rate"] = sum(bool(result.attack_success) for result in attacked) / len(attacked)
    return summary


def save_report(results: list[CaseResult], summary: dict[str, Any], out_dir: Path, meta: dict[str, Any]) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "report.json"
    report = {"meta": meta, "summary": summary, "results": [asdict(result) for result in results]}
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return path

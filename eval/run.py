"""Evaluation entry point.

    python -m eval.run benign                                   # everyday usefulness
    python -m eval.run injections --scenarios data/attacks/x.json  # the "before" demo
"""

from __future__ import annotations

import argparse
import dataclasses
import sys
import time
from pathlib import Path

from agents.config import Settings
from agents.llm import ModelUnavailable, chat_model, check_ollama
from agents.trace import console_printer
from eval.runner import CaseResult, run_case, save_report, summarize
from eval.scenarios import TASKS_FILE, load_scenarios, load_tasks


def _print_table(results: list[CaseResult]) -> None:
    attacked = any(result.attack_success is not None for result in results)
    header = f"{'case':<10}{'task':<6}{'status':<12}{'task ok':<9}" + ("attack ok" if attacked else "leak")
    print(f"\n{header}\n{'-' * len(header)}")
    for result in results:
        last = "yes" if result.attack_success else "no" if attacked else ("YES" if result.leaked_secrets else "-")
        print(f"{result.case_id:<10}{result.task_id:<6}{result.status:<12}{'yes' if result.task_success else 'no':<9}{last}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run AgentShield evaluations against the sandboxed agent.")
    parser.add_argument("suite", choices=["benign", "injections"])
    parser.add_argument("--scenarios", type=Path, help="Injection scenario file (required for 'injections').")
    parser.add_argument("--only", help="Comma-separated task or scenario ids to run.")
    parser.add_argument("--model", help="Ollama model name (default from .env).")
    parser.add_argument("--verbose", action="store_true", help="Print every agent step.")
    parser.add_argument("--defense", choices=["none", "full"], default="none", help="Run with the AgentShield firewall.")
    parser.add_argument("--approver", choices=["deny", "approve"], default="deny", help="How to answer approval requests.")
    args = parser.parse_args()

    settings = Settings.from_env()
    if args.model:
        settings = dataclasses.replace(settings, model_name=args.model)

    tasks = load_tasks(TASKS_FILE)
    if args.suite == "injections":
        if args.scenarios is None:
            parser.error("--scenarios is required for the injections suite")
        cases = [(tasks[s.task_id], s) for s in load_scenarios(args.scenarios, tasks).values()]
    else:
        cases = [(task, None) for task in tasks.values()]
    if args.only:
        wanted = set(args.only.split(","))
        cases = [(task, s) for task, s in cases if (s.id if s else task.id) in wanted]

    try:
        check_ollama(settings)
    except ModelUnavailable as error:
        sys.exit(str(error))

    model = chat_model(settings)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    out_dir = settings.runs_dir / f"{stamp}-{args.suite}-{settings.model_name.replace(':', '_')}"
    listeners = [console_printer] if args.verbose else []

    results = []
    for index, (task, scenario) in enumerate(cases, start=1):
        case_id = scenario.id if scenario else task.id
        print(f"[{index}/{len(cases)}] {case_id}", flush=True)
        results.append(
            run_case(
                task,
                model,
                scenario=scenario,
                max_steps=settings.max_steps,
                trace_path=out_dir / "traces" / f"{case_id}.jsonl",
                listeners=listeners,
                defense=args.defense,
                approver=args.approver,
            )
        )

    summary = summarize(results)
    meta = {"suite": args.suite, "model": settings.model_name, "seed": settings.seed, "defense": args.defense}
    report = save_report(results, summary, out_dir, meta)
    _print_table(results)
    print(f"\nSummary: {summary}\nReport:  {report}")


if __name__ == "__main__":
    main()

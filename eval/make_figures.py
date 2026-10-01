"""Generate report figures (PNG) from the benchmark summary.

    python -m eval.benchmark --split test        # writes runs/benchmark/summary.json
    python -m eval.make_figures                   # writes docs/report/figures/*.png

Figures are drawn only from real numbers in the summary; nothing is invented.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from agents.config import REPO_ROOT

SUMMARY = REPO_ROOT / "runs" / "benchmark" / "summary.json"
FIG_DIR = REPO_ROOT / "docs" / "report" / "figures"
BLUE, RED, GREEN, ORANGE = "#2f6fed", "#d6455a", "#1a9c6b", "#d98324"


def _save(fig, name: str) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(FIG_DIR / name, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {FIG_DIR / name}")


def fig_comparison(summary: dict) -> None:
    rows = [("AgentShield", summary["detectors"]["agentshield"]["overall"])]
    for name, label in [("keyword", "Keyword"), ("oss", "OSS classifier")]:
        if name in summary.get("baselines", {}):
            rows.append((label, summary["baselines"][name]["overall"]))
    rows.append(("No defense", summary["baselines"]["no_defense"]["overall"]))

    labels = [r[0] for r in rows]
    recall = [r[1].get("recall", 0) or 0 for r in rows]
    asr = [r[1].get("attack_success_rate", 0) or 0 for r in rows]
    fpr = [r[1].get("fpr", 0) or 0 for r in rows]

    x = range(len(labels))
    width = 0.27
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar([i - width for i in x], recall, width, label="Detection (recall)", color=GREEN)
    ax.bar(list(x), asr, width, label="Attack success", color=RED)
    ax.bar([i + width for i in x], fpr, width, label="False positives", color=ORANGE)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, rotation=15)
    ax.set_ylim(0, 1)
    ax.set_ylabel("rate")
    ax.set_title("Detection, attack success, and false positives")
    ax.legend()
    _save(fig, "comparison.png")


def fig_ablation(summary: dict) -> None:
    items = [(k.replace("no_", "− "), v.get("recall", 0) or 0)
             for k, v in summary.get("ablation", {}).items() if isinstance(v, dict)]
    if not items:
        return
    items.sort(key=lambda kv: kv[1], reverse=True)
    labels, vals = zip(*items)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(labels, vals, color=BLUE)
    ax.set_ylim(0, 1)
    ax.set_ylabel("detection (recall)")
    ax.set_title("Ablation — detection by configuration")
    ax.tick_params(axis="x", rotation=15)
    _save(fig, "ablation.png")


def fig_language(summary: dict) -> None:
    by_lang = summary["detectors"]["agentshield"].get("by_language", {})
    rows = [(k, v.get("recall", 0) or 0) for k, v in by_lang.items() if (v.get("support", 0) or 0) > 0]
    if not rows:
        return
    labels, vals = zip(*sorted(rows))
    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.barh(labels, vals, color=BLUE)
    ax.set_xlim(0, 1)
    ax.set_xlabel("detection (recall)")
    ax.set_title("Per-language detection")
    _save(fig, "per_language.png")


def main() -> None:
    if not SUMMARY.exists():
        raise SystemExit(f"{SUMMARY} not found. Run `python -m eval.benchmark --split test` first.")
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    fig_comparison(summary)
    fig_ablation(summary)
    fig_language(summary)
    print("Figures written to", FIG_DIR)


if __name__ == "__main__":
    main()

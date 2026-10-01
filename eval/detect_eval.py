"""Run a detector layer over the dataset and report per-layer, per-language, per-category metrics.

    python -m eval.detect_eval --layer rules --split test
    python -m eval.detect_eval --layer rules            # falls back to all committed data

Layer 2 needs a trained model; Layer 3 needs Ollama. When unavailable, the harness says so.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from agents.config import REPO_ROOT
from dataset.build import INPUT_DIRS, collect
from dataset.schema import read_jsonl
from shield.detectors import Context, evaluate, format_report
from shield.detectors.base import Detector
from shield.preprocess import analyze_text

SPLITS_DIR = REPO_ROOT / "data" / "generated" / "splits"


def _build_detector(layer: str) -> Detector:
    if layer == "rules":
        from shield.detectors import RuleDetector

        return RuleDetector()
    if layer == "classifier":
        from shield.detectors import ClassifierDetector

        detector = ClassifierDetector()
        if not detector.available:
            raise SystemExit("Classifier unavailable. Train it with `python -m shield.detectors.train_classifier`.")
        return detector
    if layer == "intent":
        from shield.detectors import IntentDetector, ollama_judge

        return IntentDetector(judge=ollama_judge())
    raise SystemExit(f"Unknown layer {layer!r}")


def _load_records(split: str | None):
    if split:
        path = SPLITS_DIR / f"{split}.jsonl"
        if not path.exists():
            raise SystemExit(f"{path} not found. Build splits with `python -m dataset.build`.")
        return list(read_jsonl(path))
    records, _ = collect(INPUT_DIRS)
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate one detector layer on the dataset.")
    parser.add_argument("--layer", choices=["rules", "classifier", "intent"], default="rules")
    parser.add_argument("--split", help="train/val/test/heldout; omit to use all committed data.")
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    records = _load_records(args.split)
    if args.limit:
        records = records[: args.limit]
    detector = _build_detector(args.layer)
    context = Context(user_task="")

    items: list[dict] = []
    latencies: list[float] = []
    start = time.perf_counter()
    for record in records:
        signal = detector.score(analyze_text(record.text, source=record.source), context)
        latencies.append(signal.latency_ms)
        items.append(
            {"label": record.label, "score": signal.score, "category": record.category, "language": record.language}
        )
    elapsed = time.perf_counter() - start

    report = evaluate(items, threshold=args.threshold)
    latencies.sort()
    p50 = latencies[len(latencies) // 2] if latencies else 0.0
    p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0.0

    print(f"\nLayer: {args.layer}   records: {len(records)}   wall: {elapsed:.2f}s")
    print(f"latency per chunk: p50={p50:.2f}ms p95={p95:.2f}ms")
    print("\n" + format_report(report))

    out_dir = REPO_ROOT / "runs" / "detectors"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{args.layer}-{args.split or 'all'}.json"
    out_path.write_text(
        json.dumps({"layer": args.layer, "latency_ms": {"p50": p50, "p95": p95}, **report.as_dict()}, indent=2),
        encoding="utf-8",
    )
    print(f"\nSaved {out_path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()

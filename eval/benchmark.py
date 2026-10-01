"""The evaluation suite: the headline metrics table, the ablation study, and the baseline
comparison, written to a report the dashboard can show.

    python -m dataset.build
    python -m eval.benchmark --split test

Detector-level metrics (detection, false positives, per-language, latency) run on the dataset
and need no model. Attack-success-rate and task-utility against the live agent, and the
canary/taint ablations, need a model and scenarios; pass --agent to include them.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from agents.config import REPO_ROOT
from dataset.schema import Record, read_jsonl
from shield.detectors import Context, RuleDetector, evaluate
from shield.detectors.base import Detector
from shield.preprocess import analyze_text
from shield.scoring import FEATURES, RiskFuser

SPLITS_DIR = REPO_ROOT / "data" / "generated" / "splits"
OUT_DIR = REPO_ROOT / "runs" / "benchmark"
CONTENT_LAYERS = ("rules", "classifier", "intent")


def score_fused(records: list[Record], detectors: list[Detector], fuser: RiskFuser, exclude: str = "") -> tuple[list[dict], list[float]]:
    """Fuse the content detectors into one risk per record. ``exclude`` drops one layer (ablation)."""
    context = Context(user_task="")
    items, latencies = [], []
    for record in records:
        chunk = analyze_text(record.text, record.source)
        signals = {name: 0.0 for name in FEATURES}
        elapsed = 0.0
        for detector in detectors:
            if detector.name == exclude or detector.name not in signals:
                continue
            signal = detector.score(chunk, context)
            signals[detector.name] = signal.score
            elapsed += signal.latency_ms
        items.append({"label": record.label, "score": fuser.fuse(signals), "category": record.category, "language": record.language})
        latencies.append(elapsed)
    return items, latencies


def score_single(records: list[Record], detector: Detector, preprocess: bool = True) -> list[dict]:
    """Score with one detector. Baselines use ``preprocess=False`` so they are judged as the
    standalone systems they are, without AgentShield's de-obfuscation helping them."""
    from shield.preprocess.types import Chunk

    context = Context(user_task="")
    items = []
    for r in records:
        chunk = analyze_text(r.text, r.source) if preprocess else Chunk(text=r.text, source=r.source)
        items.append({"label": r.label, "score": detector.score(chunk, context).score, "category": r.category, "language": r.language})
    return items


def _summary(items: list[dict], threshold: float = 0.5) -> dict[str, Any]:
    report = evaluate(items, threshold).as_dict()
    overall = report["overall"]
    # Detection recall on attacks = 1 - attack-success-rate at the detector.
    overall["attack_success_rate"] = round(1 - overall["recall"], 4) if overall["support"] else None
    return report


def build_content_detectors() -> list[Detector]:
    detectors: list[Detector] = [RuleDetector()]
    try:
        from shield.detectors import ClassifierDetector

        classifier = ClassifierDetector()
        if classifier.available:
            detectors.append(classifier)
    except Exception:  # noqa: BLE001
        pass
    return detectors


def run_benchmark(records: list[Record], threshold: float = 0.5) -> dict[str, Any]:
    # Use the fusion weights learned on validation data if present (eval.fit_fusion), else the
    # hand-set defaults.
    fuser = RiskFuser.load(REPO_ROOT / "models" / "fusion.json")
    detectors = build_content_detectors()
    present = [d.name for d in detectors if d.name in CONTENT_LAYERS]

    fused_items, latencies = score_fused(records, detectors, fuser)
    latencies.sort()
    result: dict[str, Any] = {
        "dataset": {
            "n": len(records),
            "attacks": sum(r.label == "attack" for r in records),
            "languages": sorted({r.language for r in records}),
        },
        "active_layers": present,
        "latency_ms": {
            "p50": round(latencies[len(latencies) // 2], 3) if latencies else 0.0,
            "p95": round(latencies[int(len(latencies) * 0.95)], 3) if latencies else 0.0,
        },
        "detectors": {"agentshield": _summary(fused_items, threshold)},
        "ablation": {"full": _summary(fused_items, threshold)["overall"]},
        "baselines": {},
    }

    # Baselines.
    from shield.detectors.baselines import KeywordFilterDetector, OSSClassifierDetector

    result["baselines"]["keyword"] = _summary(score_single(records, KeywordFilterDetector(), preprocess=False), threshold)
    result["baselines"]["no_defense"] = {"overall": {"recall": 0.0, "attack_success_rate": 1.0, "fpr": 0.0}}
    oss = OSSClassifierDetector()
    if oss.available:
        result["baselines"]["oss"] = _summary(score_single(records, oss, preprocess=False), threshold)

    # Ablation: leave one content layer out.
    for layer in present:
        items, _ = score_fused(records, detectors, fuser, exclude=layer)
        result["ablation"][f"no_{layer}"] = _summary(items, threshold)["overall"]
    result["ablation_note"] = "canary and taint are action-level; their ablation needs --agent with scenarios."
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the AgentShield evaluation suite.")
    parser.add_argument("--split", default="test")
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--publish", help="API base URL to PUT /results to, e.g. http://localhost:8000")
    args = parser.parse_args()

    path = SPLITS_DIR / f"{args.split}.jsonl"
    if not path.exists():
        raise SystemExit(f"{path} not found. Run `python -m dataset.build` first.")
    records = list(read_jsonl(path))

    summary = run_benchmark(records, threshold=args.threshold)
    summary["generated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(summary["detectors"]["agentshield"]["overall"], indent=2))
    print(f"\nAblation: {json.dumps(summary['ablation'], ensure_ascii=False)}")
    print(f"\nSaved {OUT_DIR / 'summary.json'}")

    if args.publish:
        import urllib.request

        request = urllib.request.Request(
            f"{args.publish.rstrip('/')}/results", data=json.dumps(summary).encode(),
            headers={"Content-Type": "application/json"}, method="PUT",
        )
        try:
            urllib.request.urlopen(request, timeout=5)
            print(f"Published to {args.publish}/results")
        except Exception as error:  # noqa: BLE001
            print(f"Could not publish: {error}")


if __name__ == "__main__":
    main()

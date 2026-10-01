"""Learn the risk-fusion weights on the validation split and save them.

    python -m dataset.build
    python -m eval.fit_fusion

Each validation sample is passed through the available detectors to build a feature vector,
and logistic regression fits the weights. Layers that are unavailable (no trained classifier,
no Ollama) contribute a zero feature, so the fuser simply learns to rely on what is present.
The printed weights are what the report should cite to justify the fusion.
"""

from __future__ import annotations

import argparse

from agents.config import REPO_ROOT
from dataset.schema import read_jsonl
from shield.detectors import Context, RuleDetector
from shield.detectors.base import Detector
from shield.preprocess import analyze_text
from shield.scoring import FEATURES, RiskFuser

SPLITS_DIR = REPO_ROOT / "data" / "generated" / "splits"


def featurize(records, detectors: list[Detector]) -> tuple[list[dict], list[int]]:
    context = Context(user_task="")
    rows: list[dict] = []
    labels: list[int] = []
    for record in records:
        chunk = analyze_text(record.text, record.source)
        signals = {name: 0.0 for name in FEATURES}
        for detector in detectors:
            if detector.name in signals:
                signals[detector.name] = detector.score(chunk, context).score
        rows.append(signals)
        labels.append(1 if record.label == "attack" else 0)
    return rows, labels


def main() -> None:
    parser = argparse.ArgumentParser(description="Fit the risk-fusion logistic regression.")
    parser.add_argument("--split", default="val")
    parser.add_argument("--epochs", type=int, default=800)
    parser.add_argument("--out", default=str(REPO_ROOT / "models" / "fusion.json"))
    args = parser.parse_args()

    path = SPLITS_DIR / f"{args.split}.jsonl"
    if not path.exists():
        raise SystemExit(f"{path} not found. Run `python -m dataset.build` first.")
    records = list(read_jsonl(path))

    detectors: list[Detector] = [RuleDetector()]
    try:
        from shield.detectors import ClassifierDetector

        classifier = ClassifierDetector()
        if classifier.available:
            detectors.append(classifier)
    except Exception:  # noqa: BLE001
        pass

    X, y = featurize(records, detectors)
    attacks = sum(y)
    print(f"Fitting on {len(y)} samples ({attacks} attack / {len(y) - attacks} benign) using: {[d.name for d in detectors]}")
    if attacks == 0 or attacks == len(y):
        print("WARNING: only one class present; keeping default weights (fit needs both classes).")
        RiskFuser().save(__import__("pathlib").Path(args.out))
        return

    fuser = RiskFuser().fit(X, y, epochs=args.epochs)
    from pathlib import Path

    fuser.save(Path(args.out))
    print(f"\nLearned weights: {fuser.weights}")
    print(f"Bias: {fuser.bias:.3f}")
    print(f"Saved to {args.out}")


if __name__ == "__main__":
    main()

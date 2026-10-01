"""Fine-tune xlm-roberta-base on the AgentShield dataset, then report per-category and
per-language precision/recall/F1. Intended for a GPU (Colab/Kaggle).

    pip install "agentshield[ml]"
    python -m dataset.build                       # produce data/generated/splits/
    python -m shield.detectors.train_classifier --epochs 3

Heavy imports live inside main so importing this module never requires transformers/torch.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from agents.config import REPO_ROOT
from shield.detectors.metrics import evaluate, format_report

SPLITS_DIR = REPO_ROOT / "data" / "generated" / "splits"


def _load_split(name: str) -> list[dict]:
    path = SPLITS_DIR / f"{name}.jsonl"
    if not path.exists():
        raise SystemExit(f"Missing {path}. Run `python -m dataset.build` first.")
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Fine-tune xlm-roberta-base for injection detection.")
    parser.add_argument("--base-model", default="xlm-roberta-base")
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "models" / "xlmr-injection")
    parser.add_argument("--epochs", type=float, default=3.0)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--max-length", type=int, default=256)
    args = parser.parse_args()

    import numpy as np
    import torch
    from datasets import Dataset
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        Trainer,
        TrainingArguments,
    )

    train_rows, val_rows, test_rows = _load_split("train"), _load_split("val"), _load_split("test")
    label_to_id = {"benign": 0, "attack": 1}
    tokenizer = AutoTokenizer.from_pretrained(args.base_model)

    def to_dataset(rows: list[dict]) -> Dataset:
        dataset = Dataset.from_dict(
            {
                "text": [row["text"] for row in rows],
                "label": [label_to_id[row["label"]] for row in rows],
            }
        )
        return dataset.map(
            lambda batch: tokenizer(batch["text"], truncation=True, max_length=args.max_length),
            batched=True,
        )

    train_ds, val_ds = to_dataset(train_rows), to_dataset(val_rows)
    model = AutoModelForSequenceClassification.from_pretrained(args.base_model, num_labels=2)

    training_args = TrainingArguments(
        output_dir=str(args.out / "checkpoints"),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        learning_rate=args.lr,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        logging_steps=50,
    )
    # transformers >= 4.46 / 5.x renamed Trainer's `tokenizer` arg to `processing_class`.
    trainer_kwargs = {"model": model, "args": training_args, "train_dataset": train_ds, "eval_dataset": val_ds}
    try:
        trainer = Trainer(**trainer_kwargs, processing_class=tokenizer)
    except TypeError:
        trainer = Trainer(**trainer_kwargs, tokenizer=tokenizer)
    trainer.train()

    args.out.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(args.out))
    tokenizer.save_pretrained(str(args.out))

    # Per-category / per-language report on the held-back test split.
    model.eval()
    items: list[dict] = []
    for row in test_rows:
        inputs = tokenizer(row["text"], truncation=True, max_length=args.max_length, return_tensors="pt")
        with torch.no_grad():
            prob = torch.softmax(model(**inputs).logits[0], dim=-1)[1].item()
        items.append({"label": row["label"], "score": prob, "category": row["category"], "language": row["language"]})

    report = evaluate(items)
    print("\n" + format_report(report))
    (args.out / "test_metrics.json").write_text(json.dumps(report.as_dict(), indent=2), encoding="utf-8")
    print(f"\nSaved model to {args.out} and metrics to {args.out / 'test_metrics.json'}")


if __name__ == "__main__":
    main()

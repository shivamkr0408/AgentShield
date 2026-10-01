"""Assemble every input source into deduplicated train/val/test/heldout splits.

    python -m dataset.build --heldout-category encoded_text

Inputs are every ``*.jsonl`` under the committed source dirs plus any ingested public data
in ``data/generated/``. Outputs and a ``stats.json`` are written under ``data/generated/splits/``.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from agents.config import REPO_ROOT
from dataset.schema import Record, read_jsonl, validate, write_jsonl
from dataset.splits import split

DATA_DIR = REPO_ROOT / "data"
# Committed, human-curated inputs, plus generated (ingested) inputs.
INPUT_DIRS = [DATA_DIR / "benign", DATA_DIR / "seeds", DATA_DIR / "multilingual", DATA_DIR / "generated"]
OUT_DIR = DATA_DIR / "generated" / "splits"


def collect(input_dirs: list[Path]) -> tuple[list[Record], list[str]]:
    records: list[Record] = []
    errors: list[str] = []
    for directory in input_dirs:
        if not directory.exists():
            continue
        for path in sorted(directory.rglob("*.jsonl")):
            if OUT_DIR in path.parents:  # never re-ingest our own outputs
                continue
            for record in read_jsonl(path):
                problems = validate(record)
                if problems:
                    errors.append(f"{path.relative_to(DATA_DIR)} [{record.id}]: {'; '.join(problems)}")
                else:
                    records.append(record)
    return records, errors


def _breakdown(records: list[Record]) -> dict[str, Any]:
    return {
        "total": len(records),
        "by_label": dict(Counter(r.label for r in records)),
        "by_category": dict(Counter(r.category for r in records)),
        "by_language": dict(Counter(r.language for r in records)),
        "by_source": dict(Counter(r.source.split(":")[0] for r in records)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the AgentShield dataset splits.")
    parser.add_argument("--heldout-category", default="encoded_text", help="Attack category held out for generalization.")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--strict", action="store_true", help="Fail if any input record is invalid.")
    args = parser.parse_args()

    records, errors = collect(INPUT_DIRS)
    if errors:
        print(f"{len(errors)} invalid record(s):")
        for message in errors[:20]:
            print(f"  - {message}")
        if args.strict:
            raise SystemExit(1)

    if not records:
        raise SystemExit(
            "No valid records found. Author benign samples in data/benign/, ingest public data with "
            "`python -m dataset.ingest`, and add the human multilingual set in data/multilingual/."
        )

    result = split(records, heldout_category=args.heldout_category, seed=args.seed)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stats: dict[str, Any] = {
        "seed": args.seed,
        "heldout_category": args.heldout_category,
        "duplicates_removed": result.duplicates_removed,
        "splits": {},
    }
    for name, bucket in result.as_dict().items():
        write_jsonl(bucket, OUT_DIR / f"{name}.jsonl")
        stats["splits"][name] = _breakdown(bucket)

    (OUT_DIR / "stats.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nRemoved {result.duplicates_removed} duplicate(s). Wrote splits to {OUT_DIR.relative_to(REPO_ROOT)}:")
    for name, bucket in result.as_dict().items():
        attacks = sum(r.label == "attack" for r in bucket)
        print(f"  {name:<8} {len(bucket):>5}  ({attacks} attack / {len(bucket) - attacks} benign)")
    print(f"\nFull breakdown: {OUT_DIR.relative_to(REPO_ROOT)}/stats.json")


if __name__ == "__main__":
    main()

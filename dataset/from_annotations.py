"""Convert a completed annotation CSV into schema JSONL under data/multilingual/.

    python -m dataset.from_annotations annotations.csv --out data/multilingual/batch1.jsonl

Only rows whose review_status is "approved" are exported, so unreviewed human-authored
samples never reach the dataset. The CSV columns are described in data/multilingual/GUIDELINES.md.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from dataset.schema import Record, validate, write_jsonl


def convert(csv_path: Path) -> tuple[list[Record], list[str]]:
    records: list[Record] = []
    errors: list[str] = []
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        for row_number, row in enumerate(csv.DictReader(handle), start=2):
            seed = (row.get("seed_id") or "").strip()
            if seed.startswith("EXAMPLE") or (row.get("review_status") or "").strip().lower() != "approved":
                continue
            text = (row.get("text") or "").strip()
            category = (row.get("category") or "").strip()
            label = "benign" if category.startswith("benign") else "attack"
            goal = (row.get("goal") or "").strip() or None
            record = Record(
                text=text,
                label=label,
                category=category,
                language=(row.get("language") or "en").strip(),
                source="human:multilingual",
                goal=goal if label == "attack" else None,
                parent_id=seed or None,
                meta={"author": (row.get("author") or "").strip(), "reviewer": (row.get("reviewer") or "").strip()},
            )
            problems = validate(record)
            if problems:
                errors.append(f"row {row_number} ({seed}): {'; '.join(problems)}")
            else:
                records.append(record)
    return records, errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert approved annotations to dataset JSONL.")
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    records, errors = convert(args.csv_path)
    for message in errors:
        print(f"skipped: {message}")
    written = write_jsonl(records, args.out)
    print(f"Wrote {written} approved record(s) to {args.out} ({len(errors)} skipped).")


if __name__ == "__main__":
    main()

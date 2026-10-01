"""Validate every committed dataset file and report a breakdown.

    python -m dataset.validate
"""

from __future__ import annotations

from collections import Counter

from dataset.build import INPUT_DIRS, collect


def main() -> None:
    records, errors = collect(INPUT_DIRS)
    print(f"Valid records: {len(records)}")
    print(f"  by label:    {dict(Counter(r.label for r in records))}")
    print(f"  by language: {dict(Counter(r.language for r in records))}")
    print(f"  attacks by category: {dict(Counter(r.category for r in records if r.label == 'attack'))}")

    if errors:
        print(f"\n{len(errors)} invalid record(s):")
        for message in errors:
            print(f"  - {message}")
        raise SystemExit(1)
    print("\nAll records valid.")


if __name__ == "__main__":
    main()

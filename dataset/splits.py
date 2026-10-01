"""Deduplication and a reproducible stratified 70/15/15 split with a held-out category."""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass

from dataset.schema import Record, text_hash


@dataclass
class SplitResult:
    train: list[Record]
    val: list[Record]
    test: list[Record]
    heldout: list[Record]  # every sample of the held-out attack category
    duplicates_removed: int

    def as_dict(self) -> dict[str, list[Record]]:
        return {"train": self.train, "val": self.val, "test": self.test, "heldout": self.heldout}


def deduplicate(records: list[Record]) -> tuple[list[Record], int]:
    """Drop exact-text duplicates, keeping the first. Invisible-char and homoglyph variants
    differ byte-for-byte, so they are correctly kept as distinct samples."""
    seen: set[str] = set()
    unique: list[Record] = []
    for record in records:
        key = text_hash(record.text)
        if key in seen:
            continue
        seen.add(key)
        unique.append(record)
    return unique, len(records) - len(unique)


def _split_group(group: list[Record], ratios: tuple[float, float, float]) -> tuple[list[Record], list[Record], list[Record]]:
    n = len(group)
    n_train = round(n * ratios[0])
    n_val = round(n * ratios[1])
    # Give tiny groups at least one test sample before filling train.
    if n >= 3 and n_train + n_val >= n:
        n_val = min(n_val, n - n_train)
        n_train = max(0, n - n_val - 1)
    return group[:n_train], group[n_train : n_train + n_val], group[n_train + n_val :]


def split(
    records: list[Record],
    heldout_category: str | None = None,
    ratios: tuple[float, float, float] = (0.70, 0.15, 0.15),
    seed: int = 7,
) -> SplitResult:
    """Stratify by (label, category, language) so every split mirrors the whole.

    ``heldout_category`` is pulled out entirely and never appears in train/val, so the
    test of generalization is against a technique the detector was never trained on.
    """
    if abs(sum(ratios) - 1.0) > 1e-6:
        raise ValueError("ratios must sum to 1.0")

    unique, duplicates = deduplicate(records)
    heldout = [r for r in unique if heldout_category and r.label == "attack" and r.category == heldout_category]
    remaining = [r for r in unique if not (heldout_category and r.label == "attack" and r.category == heldout_category)]

    groups: dict[tuple[str, str, str], list[Record]] = defaultdict(list)
    for record in remaining:
        groups[(record.label, record.category, record.language)].append(record)

    rng = random.Random(seed)
    train: list[Record] = []
    val: list[Record] = []
    test: list[Record] = []
    for key in sorted(groups):
        group = groups[key]
        rng.shuffle(group)
        group_train, group_val, group_test = _split_group(group, ratios)
        train += group_train
        val += group_val
        test += group_test

    for bucket in (train, val, test, heldout):
        rng.shuffle(bucket)
    return SplitResult(train, val, test, heldout, duplicates)

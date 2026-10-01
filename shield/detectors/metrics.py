"""Precision, recall, and F1 at a threshold, broken down overall, per category, per language.

Pure Python so it has no scientific-stack dependency. "attack" is the positive class.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Score:
    tp: int = 0
    fp: int = 0
    fn: int = 0
    tn: int = 0

    @property
    def support(self) -> int:
        return self.tp + self.fn  # number of true attacks

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    @property
    def fpr(self) -> float:
        return self.fp / (self.fp + self.tn) if (self.fp + self.tn) else 0.0

    def add(self, is_attack: bool, predicted_attack: bool) -> None:
        if is_attack and predicted_attack:
            self.tp += 1
        elif is_attack:
            self.fn += 1
        elif predicted_attack:
            self.fp += 1
        else:
            self.tn += 1

    def as_dict(self) -> dict[str, Any]:
        return {
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
            "fpr": round(self.fpr, 4),
            "support": self.support,
            "n": self.tp + self.fp + self.fn + self.tn,
        }


@dataclass
class Report:
    overall: Score = field(default_factory=Score)
    by_category: dict[str, Score] = field(default_factory=lambda: defaultdict(Score))
    by_language: dict[str, Score] = field(default_factory=lambda: defaultdict(Score))
    threshold: float = 0.5

    def as_dict(self) -> dict[str, Any]:
        return {
            "threshold": self.threshold,
            "overall": self.overall.as_dict(),
            "by_category": {key: value.as_dict() for key, value in sorted(self.by_category.items())},
            "by_language": {key: value.as_dict() for key, value in sorted(self.by_language.items())},
        }


def evaluate(items: list[dict[str, Any]], threshold: float = 0.5) -> Report:
    """Each item needs: label ("attack"/"benign"), score (float), category, language."""
    report = Report(threshold=threshold)
    for item in items:
        is_attack = item["label"] == "attack"
        predicted = item["score"] >= threshold
        report.overall.add(is_attack, predicted)
        report.by_category[item.get("category", "?")].add(is_attack, predicted)
        report.by_language[item.get("language", "?")].add(is_attack, predicted)
    return report


def format_report(report: Report) -> str:
    lines = [f"threshold = {report.threshold}", f"overall: {report.overall.as_dict()}", "", "by language:"]
    for language, score in sorted(report.by_language.items()):
        lines.append(f"  {language:<8} {score.as_dict()}")
    lines.append("")
    lines.append("by category:")
    for category, score in sorted(report.by_category.items()):
        lines.append(f"  {category:<22} {score.as_dict()}")
    return "\n".join(lines)

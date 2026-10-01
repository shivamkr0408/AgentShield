"""The unified sample record, its validation, and JSONL input/output."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dataset.taxonomy import (
    ATTACK_GOALS,
    EXPECTED_SCRIPT,
    KNOWN_LANGUAGES,
    KNOWN_SCRIPTS,
    categories_for,
)

_DEVANAGARI = re.compile(r"[ऀ-ॿ]")
_TAMIL = re.compile(r"[஀-௿]")
_LATIN = re.compile(r"[A-Za-z]")


def detect_script(text: str) -> str:
    """Classify the dominant script, or "mixed" when two are both substantial."""
    counts = {
        "devanagari": len(_DEVANAGARI.findall(text)),
        "tamil": len(_TAMIL.findall(text)),
        "latin": len(_LATIN.findall(text)),
    }
    total = sum(counts.values())
    if total == 0:
        return "latin"
    ranked = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    (top, top_n), (_, second_n) = ranked[0], ranked[1]
    return "mixed" if second_n >= 0.2 * total else top


def text_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]


@dataclass
class Record:
    text: str
    label: str  # "attack" or "benign"
    category: str
    language: str = "en"
    script: str = ""
    source: str = "unknown"
    goal: str | None = None
    parent_id: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)
    id: str = ""

    def __post_init__(self) -> None:
        if not self.script:
            self.script = detect_script(self.text)
        if not self.id:
            self.id = f"{self.source.split(':')[0]}:{text_hash(self.text)}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "label": self.label,
            "category": self.category,
            "language": self.language,
            "script": self.script,
            "source": self.source,
            "goal": self.goal,
            "parent_id": self.parent_id,
            "meta": self.meta,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Record:
        return cls(
            text=data["text"],
            label=data["label"],
            category=data["category"],
            language=data.get("language", "en"),
            script=data.get("script", ""),
            source=data.get("source", "unknown"),
            goal=data.get("goal"),
            parent_id=data.get("parent_id"),
            meta=data.get("meta", {}),
            id=data.get("id", ""),
        )


def validate(record: Record) -> list[str]:
    """Return a list of problems with a record; empty means valid."""
    problems: list[str] = []
    if not record.text.strip():
        problems.append("empty text")
    if record.label not in {"attack", "benign"}:
        problems.append(f"bad label {record.label!r}")
        return problems
    if record.category not in categories_for(record.label):
        problems.append(f"category {record.category!r} is not valid for label {record.label!r}")
    if record.language not in KNOWN_LANGUAGES:
        problems.append(f"unknown language {record.language!r}")
    if record.script not in KNOWN_SCRIPTS:
        problems.append(f"unknown script {record.script!r}")
    elif record.language in EXPECTED_SCRIPT and record.script not in EXPECTED_SCRIPT[record.language]:
        problems.append(f"script {record.script!r} is unexpected for language {record.language!r}")
    if record.label == "attack" and record.goal is not None and record.goal not in ATTACK_GOALS:
        problems.append(f"unknown goal {record.goal!r}")
    if record.label == "benign" and record.goal is not None:
        problems.append("benign records must not set a goal")
    return problems


def read_jsonl(path: Path) -> Iterator[Record]:
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            try:
                yield Record.from_dict(json.loads(line))
            except (json.JSONDecodeError, KeyError) as error:
                raise ValueError(f"{path.name}:{line_number}: {error}") from error


def write_jsonl(records: Iterable[Record], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
            count += 1
    return count

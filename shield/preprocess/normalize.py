"""Unicode normalization, invisible-character stripping, and homoglyph mapping.

The aim is to collapse the tricks attackers use to hide trigger words from a filter, while
not corrupting legitimate non-Latin text. In particular, ZWNJ/ZWJ are meaningful in Indic
scripts, so they are removed only when they sit between ASCII letters (a Latin-text trick).
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field

# Formatting characters that are essentially never legitimate in content and are a classic
# way to break up a trigger word (e.g. "ig​nore").
_ALWAYS_REMOVE = {
    "​",  # zero-width space
    "⁠",  # word joiner
    "﻿",  # BOM / zero-width no-break space
    "­",  # soft hyphen
    "᠎",  # Mongolian vowel separator
    "‎", "‏",  # LRM / RLM
    "‪", "‫", "‬", "‭", "‮",  # bidi embeddings/overrides
    "⁦", "⁧", "⁨", "⁩",  # bidi isolates
}
# Removed only between ASCII letters, to preserve Devanagari/Tamil usage.
_CONTEXTUAL = {"‌", "‍"}  # ZWNJ, ZWJ

# Cross-script look-alikes mapped to their Latin base. NFKC does not touch these.
_HOMOGLYPHS = {
    # Cyrillic
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c",
    "у": "y", "х": "x", "і": "i", "ј": "j", "һ": "h",
    "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M",
    "Н": "H", "О": "O", "Р": "P", "С": "C", "Т": "T",
    "Х": "X", "У": "Y",
    # Greek
    "ο": "o", "α": "a", "ε": "e", "ι": "i", "ρ": "p",
    "υ": "u", "Ο": "O", "Α": "A", "Ε": "E", "Ζ": "Z",
    "Η": "H", "Ι": "I", "Κ": "K", "Μ": "M", "Ν": "N",
    "Ρ": "P", "Τ": "T", "Χ": "X",
}


@dataclass
class NormResult:
    text: str
    invisible_removed: int = 0
    homoglyphs_mapped: int = 0
    nfkc_changed: bool = False
    reasons: list[str] = field(default_factory=list)


def strip_invisible(text: str) -> tuple[str, int]:
    out: list[str] = []
    removed = 0
    for index, char in enumerate(text):
        if char in _ALWAYS_REMOVE:
            removed += 1
            continue
        if char in _CONTEXTUAL:
            prev = text[index - 1] if index > 0 else ""
            nxt = text[index + 1] if index + 1 < len(text) else ""
            if prev.isascii() and prev.isalpha() and nxt.isascii() and nxt.isalpha():
                removed += 1
                continue
        out.append(char)
    return "".join(out), removed


def map_homoglyphs(text: str) -> tuple[str, int]:
    out: list[str] = []
    mapped = 0
    for char in text:
        replacement = _HOMOGLYPHS.get(char)
        if replacement is not None:
            out.append(replacement)
            mapped += 1
        else:
            out.append(char)
    return "".join(out), mapped


def normalize(text: str) -> NormResult:
    reasons: list[str] = []
    stripped, removed = strip_invisible(text)
    if removed:
        reasons.append(f"removed {removed} invisible character(s)")

    nfkc = unicodedata.normalize("NFKC", stripped)
    nfkc_changed = nfkc != stripped
    if nfkc_changed:
        reasons.append("NFKC normalization changed the text")

    mapped_text, mapped = map_homoglyphs(nfkc)
    if mapped:
        reasons.append(f"mapped {mapped} look-alike letter(s) to Latin")

    return NormResult(
        text=mapped_text,
        invisible_removed=removed,
        homoglyphs_mapped=mapped,
        nfkc_changed=nfkc_changed,
        reasons=reasons,
    )

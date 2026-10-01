"""Mutation operators for the adaptive attacker.

These transform an existing seed attack to probe whether the defense still catches it. The
mechanical operators (encoding, homoglyphs, invisible characters, splitting) are exactly the
obfuscations ``shield/preprocess`` is built to reverse, so running them doubles as a test of
the preprocessor. The semantic operators (paraphrase, translate, code-switch) call an injected
rewriter — an LLM — so this module never authors attack content itself.

Everything here is for evaluating AgentShield in its sandbox. It must not be pointed at any
real system.
"""

from __future__ import annotations

import base64
import codecs
import random
from collections.abc import Callable
from urllib.parse import quote

from shield.preprocess.normalize import _HOMOGLYPHS

Mutation = Callable[[str, random.Random], str]
Rewriter = Callable[[str], str]

# Latin -> look-alike, the inverse of the preprocessor's folding map (first option per letter).
_REVERSE_HOMOGLYPH: dict[str, str] = {}
for _confusable, _latin in _HOMOGLYPHS.items():
    _REVERSE_HOMOGLYPH.setdefault(_latin, _confusable)


def encode_base64(text: str, rng: random.Random) -> str:
    return base64.b64encode(text.encode()).decode()


def encode_hex(text: str, rng: random.Random) -> str:
    return text.encode().hex()


def encode_url(text: str, rng: random.Random) -> str:
    return quote(text)


def encode_rot13(text: str, rng: random.Random) -> str:
    return codecs.encode(text, "rot_13")


def substitute_homoglyphs(text: str, rng: random.Random, fraction: float = 0.3) -> str:
    out = []
    for char in text:
        swap = _REVERSE_HOMOGLYPH.get(char)
        out.append(swap if swap and rng.random() < fraction else char)
    return "".join(out)


def insert_invisible(text: str, rng: random.Random) -> str:
    """Drop zero-width spaces inside alphabetic runs."""
    out = []
    for char in text:
        out.append(char)
        if char.isalpha() and rng.random() < 0.25:
            out.append("​")
    return "".join(out)


def split_payload(text: str, rng: random.Random) -> str:
    """Break the text with spaces, as if spread across fields the agent concatenates."""
    words = text.split(" ")
    if len(words) < 2:
        return " ".join(text)
    cut = rng.randint(1, len(words) - 1)
    return " ".join(words[:cut]) + "  ...  " + " ".join(words[cut:])


MECHANICAL: dict[str, Mutation] = {
    "base64": encode_base64,
    "hex": encode_hex,
    "url": encode_url,
    "rot13": encode_rot13,
    "homoglyph": substitute_homoglyphs,
    "invisible": insert_invisible,
    "split": split_payload,
}


def semantic_mutations(rewriter: Rewriter, languages: tuple[str, ...] = ("Hindi", "Tamil")) -> dict[str, Mutation]:
    """Build LLM-driven operators from an injected rewriter. The rewriter is the only thing
    that produces new natural-language text; this project supplies the model, not the content."""

    def paraphrase(text: str, rng: random.Random) -> str:
        return rewriter(f"Rewrite this sentence with the same meaning but different words:\n{text}")

    def code_switch(text: str, rng: random.Random) -> str:
        return rewriter(f"Rewrite this mixing English and Hindi (Hinglish), keeping the meaning:\n{text}")

    operators: dict[str, Mutation] = {"paraphrase": paraphrase, "code_switch": code_switch}
    for language in languages:
        operators[f"translate_{language.lower()}"] = (
            lambda text, rng, lang=language: rewriter(f"Translate this into {lang}, keeping the meaning:\n{text}")
        )
    return operators


def all_mutations(rewriter: Rewriter | None = None) -> dict[str, Mutation]:
    operators = dict(MECHANICAL)
    if rewriter is not None:
        operators.update(semantic_mutations(rewriter))
    return operators

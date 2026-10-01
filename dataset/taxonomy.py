"""The label and category taxonomy, plus language and script vocabularies."""

from __future__ import annotations

# Attack techniques, from the Phase 2 plan. "image_text" covers text transcribed from an
# image; in a text-only pipeline its transcription is stored and the image kept in meta.
ATTACK_CATEGORIES: dict[str, str] = {
    "instruction_override": "Tells the model to disregard its prior instructions and follow new ones.",
    "role_hijacking": "Reassigns the model's role or identity, e.g. a fake system or developer message.",
    "hidden_html": "Payload hidden from a human reader in HTML or Markdown (display:none, comments, alt text).",
    "encoded_text": "Payload encoded to slip past text filters (base64, hex, ROT13, URL-encoding).",
    "invisible_chars": "Payload carried by zero-width or bidi control characters.",
    "homoglyph": "Payload disguised with look-alike letters from other scripts.",
    "image_text": "Payload delivered as text rendered inside an image; stored here as its transcription.",
    # A catch-all for bulk public samples that arrive without a fine-grained technique label.
    "unknown": "Attack whose technique has not yet been labelled (common for ingested public data).",
}

# Attacker objectives, tracked separately from technique because they cut across it.
ATTACK_GOALS: set[str] = {
    "action_hijack",     # make the agent take an unwanted action
    "data_exfiltration",  # make the agent leak data out of its boundary
    "prompt_leak",       # make the agent reveal its system prompt
    "misinformation",    # make the agent report something false
    "denial",            # make the agent refuse or stall
    "unknown",
}

# Benign categories. The non-plain ones are deliberate hard negatives: benign text that
# uses imperative or "instruction" language and must NOT be flagged.
BENIGN_CATEGORIES: dict[str, str] = {
    "benign_plain": "Ordinary content with no imperative framing.",
    "benign_instructional": "Manuals, recipes, and how-tos that legitimately use 'instructions' and commands.",
    "benign_quoted": "Text that quotes or describes an instruction without issuing it to the agent.",
    "benign_technical": "Code, config, and logs whose imperative wording is about the software, not the agent.",
}

# Language tags. Code-mixed variants use a "-Latn" (romanized) suffix.
KNOWN_LANGUAGES: dict[str, str] = {
    "en": "English",
    "hi": "Hindi (Devanagari)",
    "ta": "Tamil",
    "hi-Latn": "Hinglish (romanized Hindi / code-mixed)",
    "ta-Latn": "Tanglish (romanized Tamil / code-mixed)",
}

KNOWN_SCRIPTS: set[str] = {"latin", "devanagari", "tamil", "mixed"}

# The script each language is expected to be written in, for a consistency check.
EXPECTED_SCRIPT: dict[str, set[str]] = {
    "en": {"latin"},
    "hi": {"devanagari", "mixed"},
    "ta": {"tamil", "mixed"},
    "hi-Latn": {"latin", "mixed"},
    "ta-Latn": {"latin", "mixed"},
}


def categories_for(label: str) -> dict[str, str]:
    if label == "attack":
        return ATTACK_CATEGORIES
    if label == "benign":
        return BENIGN_CATEGORIES
    raise ValueError(f"Unknown label {label!r}")

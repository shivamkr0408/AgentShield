"""Turn a piece of untrusted content into analyzed chunks with provenance and
obfuscation metadata. This is the entry point the detectors consume."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from shield.preprocess.encodings import decode_all
from shield.preprocess.html_extract import extract_html
from shield.preprocess.normalize import normalize
from shield.preprocess.types import Chunk

DEFAULT_MAX_CHARS = 1000


def _split_paragraphs(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text] if text.strip() else []
    chunks: list[str] = []
    current = ""
    for paragraph in text.split("\n"):
        if current and len(current) + len(paragraph) + 1 > max_chars:
            chunks.append(current)
            current = ""
        current = f"{current}\n{paragraph}" if current else paragraph
    if current.strip():
        chunks.append(current)
    return chunks


def analyze_segment(
    raw: str,
    source: str,
    origin: str,
    index: int = 0,
    hidden: bool = False,
    extra_reasons: list[str] | None = None,
    visible_text: str | None = None,
) -> Chunk:
    """Normalize and de-obfuscate one segment, appending any decoded payloads to ``text``."""
    norm = normalize(raw)
    decodings = decode_all(norm.text)
    strong = [decoding for decoding in decodings if decoding.strong]
    decoded_texts = [decoding.text for decoding in decodings]

    # Only strong decodings (base64/hex/url) are appended to the analyzed text. Speculative
    # ROT13 stays in .decoded so it does not inflate every chunk; detectors scan both.
    text = norm.text
    if strong:
        text = norm.text + "\n[decoded]\n" + "\n".join(decoding.text for decoding in strong)

    reasons = list(extra_reasons or []) + norm.reasons
    for decoding in strong:
        reasons.append(f"decoded {decoding.method}")

    return Chunk(
        text=text,
        source=source,
        origin=origin,
        index=index,
        visible_text=visible_text if visible_text is not None else ("" if hidden else raw),
        hidden_text=raw if hidden else "",
        normalized_text=norm.text,
        decoded=decoded_texts,
        hidden=hidden,
        encoded=bool(strong),
        homoglyph=norm.homoglyphs_mapped > 0,
        invisible=norm.invisible_removed > 0,
        reasons=reasons,
    )


def preprocess_text(raw: str, source: str, max_chars: int = DEFAULT_MAX_CHARS) -> list[Chunk]:
    return [
        analyze_segment(part, source, "text", index=index)
        for index, part in enumerate(_split_paragraphs(raw, max_chars))
    ]


def preprocess_html(raw: str, source: str, max_chars: int = DEFAULT_MAX_CHARS) -> list[Chunk]:
    """Visible and hidden HTML text become separate chunks; the hidden chunk records how."""
    extracted = extract_html(raw)
    chunks = [
        analyze_segment(part, source, "html", index=index)
        for index, part in enumerate(_split_paragraphs(extracted.visible, max_chars))
    ]
    if extracted.hidden.strip():
        chunks.append(
            analyze_segment(
                extracted.hidden, source, "html", index=len(chunks),
                hidden=True, extra_reasons=["hidden from reader: " + ", ".join(extracted.reasons)],
            )
        )
    return chunks


def preprocess_image(path: Path | str, source: str, ocr: Callable[[Path | str], str]) -> list[Chunk]:
    chunk = analyze_segment(ocr(path), source, "image", extra_reasons=["text read from image via OCR"])
    chunk.meta["ocr"] = True
    return [chunk]


def preprocess_pdf(path: Path | str, source: str, ocr: Callable[[Path | str], list[str]]) -> list[Chunk]:
    chunks = []
    for index, page_text in enumerate(ocr(path)):
        chunk = analyze_segment(page_text, source, "pdf", index=index, extra_reasons=[f"PDF page {index + 1}"])
        chunk.meta["ocr"] = True
        chunks.append(chunk)
    return chunks


def analyze_text(raw: str, source: str = "unknown") -> Chunk:
    """Analyze a short string as a single chunk; used to feed dataset samples to detectors."""
    return analyze_segment(raw, source, "text")

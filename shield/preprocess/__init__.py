"""Normalization, de-obfuscation, and language identification for untrusted content.

Public API:
    preprocess_text / preprocess_html / preprocess_image / preprocess_pdf -> list[Chunk]
    analyze_text(text, source) -> Chunk        (single-chunk convenience)
    normalize, decode_all, extract_html         (the individual stages)
"""

from shield.preprocess.encodings import Decoding, decode_all
from shield.preprocess.html_extract import HtmlText, extract_html
from shield.preprocess.normalize import NormResult, normalize
from shield.preprocess.ocr import OcrUnavailable, image_ocr, pdf_ocr
from shield.preprocess.pipeline import (
    analyze_segment,
    analyze_text,
    preprocess_html,
    preprocess_image,
    preprocess_pdf,
    preprocess_text,
)
from shield.preprocess.types import Chunk

__all__ = [
    "Chunk", "Decoding", "HtmlText", "NormResult", "OcrUnavailable",
    "analyze_segment", "analyze_text", "decode_all", "extract_html", "image_ocr",
    "normalize", "pdf_ocr", "preprocess_html", "preprocess_image", "preprocess_pdf", "preprocess_text",
]

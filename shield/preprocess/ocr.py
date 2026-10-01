"""Optical character recognition for images and PDF pages, via Tesseract.

OCR needs the Tesseract binary plus optional Python packages, which are not required to run
the rest of AgentShield. The functions here raise ``OcrUnavailable`` with install hints when
those are missing, and callers inject these as the ``ocr`` argument to the pipeline so tests
can supply a fake instead.

Install:  pip install "agentshield[ocr]"  and the Tesseract binary (and Poppler for PDFs).
"""

from __future__ import annotations

from pathlib import Path


class OcrUnavailable(RuntimeError):
    pass


def image_ocr(path: Path | str) -> str:
    """Return the text Tesseract reads from an image file."""
    try:
        import pytesseract
        from PIL import Image
    except ImportError as error:
        raise OcrUnavailable(
            'OCR needs Pillow and pytesseract: pip install "agentshield[ocr]" (plus the Tesseract binary).'
        ) from error
    try:
        return pytesseract.image_to_string(Image.open(path))
    except Exception as error:  # noqa: BLE001 - surfaced as a clear, catchable error
        raise OcrUnavailable(f"Tesseract failed on {path}: {error}") from error


def pdf_ocr(path: Path | str) -> list[str]:
    """Return one string per PDF page: its embedded text, or OCR of the rendered page."""
    try:
        import fitz  # PyMuPDF
    except ImportError as error:
        raise OcrUnavailable('PDF OCR needs PyMuPDF: pip install "agentshield[ocr]".') from error

    pages: list[str] = []
    with fitz.open(path) as document:
        for page in document:
            text = page.get_text().strip()
            if not text:
                import io

                pixmap = page.get_pixmap(dpi=200)
                text = image_ocr_bytes(pixmap.tobytes("png"))
            pages.append(text)
    return pages


def image_ocr_bytes(data: bytes) -> str:
    try:
        import io

        import pytesseract
        from PIL import Image
    except ImportError as error:
        raise OcrUnavailable('OCR needs Pillow and pytesseract: pip install "agentshield[ocr]".') from error
    return pytesseract.image_to_string(Image.open(io.BytesIO(data)))

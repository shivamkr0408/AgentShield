"""Decode the common encodings attackers use to slip a payload past a text filter.

Base64, hex, and percent-encoding are reported as real decodings (they set the chunk's
``encoded`` flag). ROT13 is offered as an extra candidate for detectors to scan but does not
by itself mark the chunk encoded, because almost any text "decodes" under ROT13.
"""

from __future__ import annotations

import base64
import binascii
import codecs
import re
from dataclasses import dataclass
from urllib.parse import unquote

_BASE64 = re.compile(r"[A-Za-z0-9+/]{16,}={0,2}")
_HEX = re.compile(r"(?:[0-9a-fA-F]{2}){8,}")
_PERCENT = re.compile(r"%[0-9a-fA-F]{2}")


@dataclass(frozen=True)
class Decoding:
    method: str
    text: str
    strong: bool  # True for base64/hex/url; False for speculative ROT13


def _printable(text: str) -> bool:
    if not text:
        return False
    printable = sum(char.isprintable() or char in "\n\t " for char in text)
    return printable / len(text) >= 0.9


def _try_base64(text: str) -> list[Decoding]:
    found: list[Decoding] = []
    for match in _BASE64.finditer(text):
        token = match.group()
        if len(token) % 4:
            continue
        try:
            decoded = base64.b64decode(token, validate=True).decode("utf-8", "strict")
        except (binascii.Error, UnicodeDecodeError, ValueError):
            continue
        if _printable(decoded) and decoded.strip():
            found.append(Decoding("base64", decoded, strong=True))
    return found


def _try_hex(text: str) -> list[Decoding]:
    found: list[Decoding] = []
    for match in _HEX.finditer(text):
        try:
            decoded = bytes.fromhex(match.group()).decode("utf-8", "strict")
        except (ValueError, UnicodeDecodeError):
            continue
        if _printable(decoded) and decoded.strip():
            found.append(Decoding("hex", decoded, strong=True))
    return found


def _try_url(text: str) -> list[Decoding]:
    # Two or more escapes anywhere (not necessarily consecutive), so space-separated payloads
    # like "send%20to%20..." are decoded while a stray "%" in benign text is not.
    if len(_PERCENT.findall(text)) < 2:
        return []
    decoded = unquote(text)
    return [Decoding("url", decoded, strong=True)] if decoded != text and _printable(decoded) else []


def _try_rot13(text: str) -> list[Decoding]:
    if not any(char.isalpha() for char in text):
        return []
    decoded = codecs.encode(text, "rot_13")
    return [Decoding("rot13", decoded, strong=False)] if decoded != text else []


def decode_all(text: str) -> list[Decoding]:
    """Return every recovered decoding, strong ones first."""
    decodings = _try_base64(text) + _try_hex(text) + _try_url(text) + _try_rot13(text)
    # De-duplicate on (method, text) while preserving order.
    seen: set[tuple[str, str]] = set()
    unique: list[Decoding] = []
    for decoding in decodings:
        key = (decoding.method, decoding.text)
        if key not in seen:
            seen.add(key)
            unique.append(decoding)
    return unique

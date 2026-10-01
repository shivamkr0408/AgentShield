"""The chunk produced by preprocessing, with the provenance and obfuscation metadata
that every later layer reads."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Chunk:
    # The text detectors should analyze: normalized, de-obfuscated, with any decoded
    # payloads appended. This is never shown back to the user.
    text: str
    source: str = "unknown"          # provenance, e.g. "web:http://acme.test/reviews"
    origin: str = "text"             # "text", "html", "image", or "pdf"
    index: int = 0                   # position within the source document

    visible_text: str = ""           # what a human reader would see
    hidden_text: str = ""            # text hidden from a human reader
    normalized_text: str = ""        # after normalization, before decoded payloads are appended
    decoded: list[str] = field(default_factory=list)  # payloads recovered from encodings

    hidden: bool = False             # hiding occurred in this chunk
    encoded: bool = False            # an encoding was decoded in this chunk
    homoglyph: bool = False          # look-alike letters were mapped
    invisible: bool = False          # invisible characters were stripped

    reasons: list[str] = field(default_factory=list)  # human-readable notes on what was found
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def obfuscated(self) -> bool:
        return self.hidden or self.encoded or self.homoglyph or self.invisible

    def to_dict(self) -> dict[str, Any]:
        data = {key: value for key, value in self.__dict__.items()}
        data["obfuscated"] = self.obfuscated
        return data

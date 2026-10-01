"""Separate the visible text of an HTML document from text hidden from a human reader,
recording how each hidden region was concealed."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser

_SKIP_TAGS = {"script", "style", "head", "title", "meta", "link"}
_BLOCK_TAGS = {"p", "div", "li", "tr", "br", "h1", "h2", "h3", "h4", "article", "section", "ul", "ol", "table"}


def _hidden_reason(tag: str, attrs: dict[str, str]) -> str | None:
    """Return why an element is hidden from a human reader, or None if it is visible."""
    if attrs.get("hidden") is not None:
        return f"<{tag} hidden>"
    if attrs.get("aria-hidden", "").lower() == "true":
        return f"<{tag} aria-hidden>"
    style = attrs.get("style", "").lower().replace(" ", "")
    if "display:none" in style:
        return "display:none"
    if "visibility:hidden" in style:
        return "visibility:hidden"
    if "opacity:0" in style:
        return "opacity:0"
    if re.search(r"font-size:0(px|em|%)?(;|$)", style):
        return "font-size:0"
    if re.search(r"(left|top|right|bottom):-\d{3,}", style):
        return "positioned off-screen"
    if re.search(r"color:(#fff(fff)?|white|rgb\(255,255,255\))", style):
        return "white text"
    return None


@dataclass
class HtmlText:
    visible: str
    hidden: str
    reasons: list[str] = field(default_factory=list)


class _Analyzer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._visible: list[str] = []
        self._hidden: list[str] = []
        self.reasons: list[str] = []
        self._skip_depth = 0
        self._hidden_stack: list[str] = []  # reasons for currently-open hidden ancestors

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
            return
        reason = _hidden_reason(tag, {key: value or "" for key, value in attrs})
        if reason:
            self._hidden_stack.append(reason)
            if reason not in self.reasons:
                self.reasons.append(reason)
        elif self._is_void(tag):
            return
        else:
            # Push a sentinel so end-tag bookkeeping stays balanced for non-hidden tags.
            self._hidden_stack.append("")
        if tag in _BLOCK_TAGS:
            (self._hidden if self._hidden_stack and self._hidden_stack[-1] else self._visible).append("\n")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        pass  # void elements carry no text

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
        elif not self._is_void(tag) and self._hidden_stack:
            self._hidden_stack.pop()

    def handle_comment(self, data: str) -> None:
        if data.strip():
            self._hidden.append(data)
            if "html comment" not in self.reasons:
                self.reasons.append("html comment")

    def handle_data(self, data: str) -> None:
        if self._skip_depth or not data.strip():
            return
        if any(self._hidden_stack):
            self._hidden.append(data)
        else:
            self._visible.append(data)

    @staticmethod
    def _is_void(tag: str) -> bool:
        return tag in {"br", "img", "input", "hr", "meta", "link"}

    @staticmethod
    def _clean(parts: list[str]) -> str:
        text = "".join(parts)
        lines = (" ".join(line.split()) for line in text.splitlines())
        return "\n".join(line for line in lines if line)

    def result(self) -> HtmlText:
        return HtmlText(self._clean(self._visible), self._clean(self._hidden), self.reasons)


def extract_html(html: str) -> HtmlText:
    analyzer = _Analyzer()
    analyzer.feed(html)
    analyzer.close()
    return analyzer.result()

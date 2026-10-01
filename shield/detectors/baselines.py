"""Baseline detectors for the evaluation comparison.

- KeywordFilterDetector: a naive English keyword filter, the simplest baseline.
- OSSClassifierDetector: an existing open-source prompt-injection classifier from the Hugging
  Face Hub, loaded on demand; degrades gracefully if transformers/torch or the model are absent.
"""

from __future__ import annotations

import re

from shield.detectors.base import Context, Signal, timed
from shield.preprocess.types import Chunk

_KEYWORDS = [
    "ignore previous", "ignore all previous", "disregard previous", "disregard all",
    "forget everything", "system prompt", "you are now", "act as", "new instructions",
    "do not tell", "reveal the", "send the password", "api key",
]
_KEYWORD_RE = re.compile("|".join(re.escape(k) for k in _KEYWORDS), re.I)


class KeywordFilterDetector:
    name = "keyword"

    def score(self, chunk: Chunk, context: Context) -> Signal:
        def run() -> Signal:
            matches = _KEYWORD_RE.findall(chunk.text)
            score = min(1.0, 0.5 * len(set(m.lower() for m in matches)))
            reason = f"matched: {', '.join(sorted(set(matches)))}" if matches else "no keyword matched"
            return Signal.from_score(score, reason, layer="baseline", evidence=matches)

        return timed(run)


class OSSClassifierDetector:
    name = "oss"

    def __init__(self, model_name: str = "protectai/deberta-v3-base-prompt-injection-v2", threshold: float = 0.5) -> None:
        self.model_name = model_name
        self.threshold = threshold
        self._pipe = None
        self._error = ""
        try:
            from transformers import pipeline

            self._pipe = pipeline("text-classification", model=model_name, truncation=True, max_length=256)
        except Exception as error:  # noqa: BLE001 - no network/model/deps -> unavailable
            self._error = f"OSS classifier unavailable: {error}"

    @property
    def available(self) -> bool:
        return self._pipe is not None

    def score(self, chunk: Chunk, context: Context) -> Signal:
        def run() -> Signal:
            if not self.available:
                return Signal(0.0, self._error, label="uncertain", layer="baseline")
            prediction = self._pipe(chunk.text)[0]
            label = str(prediction["label"]).upper()
            prob = float(prediction["score"])
            injection = prob if label in {"INJECTION", "LABEL_1", "UNSAFE", "JAILBREAK"} else 1.0 - prob
            return Signal.from_score(injection, f"{self.model_name}: {label} {prob:.2f}", layer="baseline", threshold=self.threshold)

        return timed(run)

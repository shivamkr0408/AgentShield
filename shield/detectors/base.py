"""The shared detector interface.

Every layer implements ``score(chunk, context) -> Signal``. A ``Signal`` unpacks to the
``(score, reason)`` pair the plan specifies, while also carrying a label, the layer name,
evidence, and latency for the dashboard and the metrics.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from shield.preprocess.types import Chunk


@dataclass
class Context:
    """What the agent was actually asked to do, so a layer can judge divergence."""

    user_task: str = ""


@dataclass
class Signal:
    score: float               # P(injection) in [0, 1]
    reason: str                # one-line, human-readable
    label: str = "uncertain"   # "attack", "benign", or "uncertain"
    layer: str = ""
    evidence: list[str] = field(default_factory=list)
    latency_ms: float = 0.0

    def __iter__(self) -> Iterator[object]:
        # Supports: score, reason = detector.score(chunk, context)
        yield self.score
        yield self.reason

    @classmethod
    def from_score(cls, score: float, reason: str, layer: str, threshold: float = 0.5, **kw: object) -> Signal:
        score = max(0.0, min(1.0, score))
        label = "attack" if score >= threshold else "benign"
        return cls(score=score, reason=reason, label=label, layer=layer, **kw)  # type: ignore[arg-type]


@runtime_checkable
class Detector(Protocol):
    name: str

    def score(self, chunk: Chunk, context: Context) -> Signal: ...


def timed(func: Callable[[], Signal]) -> Signal:
    """Run a scoring function and record its latency on the returned signal."""
    start = time.perf_counter()
    signal = func()
    signal.latency_ms = (time.perf_counter() - start) * 1000
    return signal

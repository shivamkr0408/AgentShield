"""Fuse the per-layer signals into one risk score with logistic regression.

Weights are learned on validation data by ``eval.fit_fusion`` and loaded here; sensible
hand-set defaults let the firewall run before any training. The model is deliberately a
linear-plus-sigmoid so each layer's contribution is readable (``explain``), which is what the
report needs to justify the fusion.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

# Fixed feature order. Each is a per-action signal in [0, 1].
FEATURES: tuple[str, ...] = ("rules", "classifier", "intent", "canary", "taint")

# Hand-set defaults: canary and taint are high-precision, so they carry most weight, but any
# single layer at full confidence still clears the sanitize threshold (so an L1-only
# deployment, with no trained classifier or LLM judge, still reacts to a blatant injection).
_DEFAULT_WEIGHTS = {"rules": 3.5, "classifier": 3.5, "intent": 3.0, "canary": 6.0, "taint": 4.0}
_DEFAULT_BIAS = -3.0


def _sigmoid(x: float) -> float:
    if x < -60:
        return 0.0
    if x > 60:
        return 1.0
    return 1.0 / (1.0 + math.exp(-x))


@dataclass
class RiskFuser:
    weights: dict[str, float] = field(default_factory=lambda: dict(_DEFAULT_WEIGHTS))
    bias: float = _DEFAULT_BIAS

    def _logit(self, signals: dict[str, float]) -> float:
        return self.bias + sum(self.weights.get(name, 0.0) * float(signals.get(name, 0.0)) for name in FEATURES)

    def fuse(self, signals: dict[str, float]) -> float:
        return _sigmoid(self._logit(signals))

    def explain(self, signals: dict[str, float]) -> list[tuple[str, float]]:
        """Each feature's contribution to the logit, largest magnitude first."""
        contributions = [("bias", self.bias)]
        contributions += [(name, self.weights.get(name, 0.0) * float(signals.get(name, 0.0))) for name in FEATURES]
        return sorted(contributions, key=lambda item: abs(item[1]), reverse=True)

    def fit(self, X: list[dict[str, float]], y: list[int], epochs: int = 500, lr: float = 0.1, l2: float = 1e-3) -> RiskFuser:
        """Batch gradient descent on binary cross-entropy. Pure Python, no numpy needed."""
        if not X:
            raise ValueError("no training rows")
        n = len(X)
        for _ in range(epochs):
            grad_w = {name: 0.0 for name in FEATURES}
            grad_b = 0.0
            for row, label in zip(X, y):
                error = self.fuse(row) - label
                grad_b += error
                for name in FEATURES:
                    grad_w[name] += error * float(row.get(name, 0.0))
            self.bias -= lr * (grad_b / n)
            for name in FEATURES:
                self.weights[name] -= lr * (grad_w[name] / n + l2 * self.weights[name])
        return self

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"weights": self.weights, "bias": self.bias}, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> RiskFuser:
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(weights={**_DEFAULT_WEIGHTS, **data.get("weights", {})}, bias=data.get("bias", _DEFAULT_BIAS))

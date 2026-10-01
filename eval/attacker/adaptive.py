"""The adaptive attacker loop.

Starting from seed attacks the dataset supplies, it mutates them, tests them against a target
defense, reads back feedback shaped by the threat model, and keeps the most evasive variants
under a fixed query budget. It reports the attack-success rate as a function of budget and the
set of successful evasions, which can be fed back into classifier training.

This evaluates a defender in its sandbox. Seeds come from the dataset, never from this module.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol

from eval.attacker.mutations import Mutation, all_mutations


class ThreatModel(StrEnum):
    BLACK_BOX = "black"   # attacker sees only whether the attack was blocked
    GRAY_BOX = "gray"     # also sees which layer blocked it
    WHITE_BOX = "white"   # also sees the risk score


@dataclass
class AttackOutcome:
    text: str
    blocked: bool
    score: float = 0.0
    layer: str = ""
    lineage: list[str] = field(default_factory=list)  # the mutation chain that produced it


class Target(Protocol):
    def evaluate(self, text: str) -> AttackOutcome: ...


@dataclass
class DetectorTarget:
    """Wraps a detector (or the fused shield) so the attacker can probe it."""

    detector: object
    threshold: float = 0.5

    def evaluate(self, text: str) -> AttackOutcome:
        from shield.detectors.base import Context
        from shield.preprocess import analyze_text

        signal = self.detector.score(analyze_text(text, "attacker"), Context(user_task=""))
        return AttackOutcome(text=text, blocked=signal.score >= self.threshold, score=signal.score, layer=signal.layer)


@dataclass
class AttackReport:
    seeds: int
    queries: int
    successes: list[AttackOutcome]
    asr_curve: list[tuple[int, float]]          # (queries used, cumulative ASR)
    bypasses_by_operator: dict[str, int]        # which final operator produced an evasion

    @property
    def attack_success_rate(self) -> float:
        return self.asr_curve[-1][1] if self.asr_curve else 0.0

    def as_dict(self) -> dict:
        return {
            "seeds": self.seeds,
            "queries": self.queries,
            "attack_success_rate": round(self.attack_success_rate, 4),
            "successes": len(self.successes),
            "asr_curve": self.asr_curve,
            "bypasses_by_operator": self.bypasses_by_operator,
        }


def _visible_score(outcome: AttackOutcome, threat: ThreatModel) -> float:
    """What the attacker can optimize on, given its feedback. Lower is more evasive."""
    if threat is ThreatModel.WHITE_BOX:
        return outcome.score
    # Black/gray box: the attacker only knows blocked or not (gray also knows the layer,
    # which steers operator choice but not the numeric objective).
    return 1.0 if outcome.blocked else 0.0


class AdaptiveAttacker:
    def __init__(
        self,
        target: Target,
        threat: ThreatModel = ThreatModel.GRAY_BOX,
        rewriter: Callable[[str], str] | None = None,
        budget: int = 60,
        pool_size: int = 8,
        seed: int = 7,
    ) -> None:
        self.target = target
        self.threat = threat
        self.operators = all_mutations(rewriter)
        self.budget = budget
        self.pool_size = pool_size
        self.rng = random.Random(seed)

    def run(self, seeds: list[str]) -> AttackReport:
        if not seeds:
            raise ValueError("the adaptive attacker needs seed attacks from the dataset")

        pool: list[AttackOutcome] = []
        successes: list[AttackOutcome] = []
        bypasses: dict[str, int] = {}
        asr_curve: list[tuple[int, float]] = []
        queries = 0
        attempts = 0

        def register(outcome: AttackOutcome) -> None:
            nonlocal attempts
            attempts += 1
            if not outcome.blocked:
                successes.append(outcome)
                last = outcome.lineage[-1] if outcome.lineage else "seed"
                bypasses[last] = bypasses.get(last, 0) + 1
            asr_curve.append((queries, round(len(successes) / attempts, 4)))

        for seed_text in seeds:
            if queries >= self.budget:
                break
            outcome = self.target.evaluate(seed_text)
            queries += 1
            register(outcome)
            pool.append(outcome)

        operator_names = list(self.operators)
        while queries < self.budget and pool:
            pool.sort(key=lambda o: _visible_score(o, self.threat))
            parent = pool[0] if self.rng.random() < 0.7 else self.rng.choice(pool)
            name = self.rng.choice(operator_names)
            try:
                child_text = self.operators[name](parent.text, self.rng)
            except Exception:  # noqa: BLE001 - a bad rewrite just wastes a mutation, not the run
                continue
            outcome = self.target.evaluate(child_text)
            outcome.lineage = [*parent.lineage, name]
            queries += 1
            register(outcome)
            pool.append(outcome)
            pool = sorted(pool, key=lambda o: _visible_score(o, self.threat))[: self.pool_size]

        return AttackReport(len(seeds), queries, successes, asr_curve, bypasses)

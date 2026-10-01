"""Heuristic, classifier, and LLM-judge prompt-injection detectors.

All three share one interface: ``score(chunk, context) -> Signal``, where ``Signal`` unpacks
to ``(score, reason)``.

    L1  RuleDetector        fast multilingual patterns + structural signals (<5 ms)
    L2  ClassifierDetector  fine-tuned xlm-roberta-base (graceful if no model)
    L3  IntentDetector      task-vs-content judge via a local LLM (+ optional embeddings)
"""

from shield.detectors.base import Context, Detector, Signal
from shield.detectors.classifier import ClassifierDetector
from shield.detectors.intent import IntentDetector, ollama_judge, parse_judgement
from shield.detectors.metrics import Report, Score, evaluate, format_report
from shield.detectors.rules import RuleDetector

__all__ = [
    "ClassifierDetector", "Context", "Detector", "IntentDetector", "Report", "RuleDetector",
    "Score", "Signal", "evaluate", "format_report", "ollama_judge", "parse_judgement",
]

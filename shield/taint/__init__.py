"""Provenance labels and taint propagation from untrusted sources to tool calls."""

from shield.taint.tracker import (
    Origin,
    TaintDecision,
    TaintState,
    TaintTracker,
    TaintVerdict,
    is_external_destination,
    label_of,
)

__all__ = [
    "Origin", "TaintDecision", "TaintState", "TaintTracker", "TaintVerdict",
    "is_external_destination", "label_of",
]

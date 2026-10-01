"""Policy engine that allows, sanitizes, confirms, or blocks agent actions."""

from shield.firewall.firewall import (
    ApprovalRequest,
    Approver,
    Firewall,
    auto_approve,
    build_firewall,
    deny_all,
)
from shield.firewall.policy import Policy, Profile, Thresholds
from shield.firewall.sanitize import sanitize, split_sentences

__all__ = [
    "ApprovalRequest", "Approver", "Firewall", "Policy", "Profile", "Thresholds",
    "auto_approve", "build_firewall", "deny_all", "sanitize", "split_sentences",
]

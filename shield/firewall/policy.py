"""The YAML-backed firewall policy: per-profile tool permissions, approval rules, thresholds."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from agents.config import REPO_ROOT

DEFAULT_POLICY_PATH = REPO_ROOT / "config" / "firewall.yaml"


@dataclass(frozen=True)
class Profile:
    name: str
    allow_tools: frozenset[str]
    always_approve: frozenset[str]
    internal_domains: frozenset[str]


@dataclass(frozen=True)
class Thresholds:
    sanitize: float = 0.5
    block_content: float = 0.85
    block_action: float = 0.9


@dataclass
class Policy:
    profiles: dict[str, Profile]
    thresholds: Thresholds
    approval_timeout_seconds: float

    def profile(self, name: str = "default") -> Profile:
        if name not in self.profiles:
            raise KeyError(f"No firewall profile {name!r}. Available: {', '.join(sorted(self.profiles))}")
        return self.profiles[name]

    @classmethod
    def load(cls, path: Path = DEFAULT_POLICY_PATH) -> Policy:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        profiles = {
            name: Profile(
                name=name,
                allow_tools=frozenset(spec.get("allow_tools", [])),
                always_approve=frozenset(spec.get("always_approve", [])),
                internal_domains=frozenset(spec.get("internal_domains", [])),
            )
            for name, spec in data.get("profiles", {}).items()
        }
        thresholds = Thresholds(**data.get("thresholds", {}))
        return cls(
            profiles=profiles,
            thresholds=thresholds,
            approval_timeout_seconds=float(data.get("approval_timeout_seconds", 30)),
        )

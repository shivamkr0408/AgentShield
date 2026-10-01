"""Runtime settings, read from environment variables or a local .env file."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    model_url: str = "http://localhost:11434"
    model_name: str = "qwen2.5:7b"
    seed: int = 7
    num_ctx: int = 8192
    max_steps: int = 12
    runs_dir: Path = REPO_ROOT / "runs"

    @classmethod
    def from_env(cls) -> Settings:
        load_dotenv(REPO_ROOT / ".env")
        defaults = cls()
        return cls(
            model_url=os.getenv("AGENTSHIELD_MODEL_URL", defaults.model_url),
            model_name=os.getenv("AGENTSHIELD_MODEL_NAME", defaults.model_name),
            seed=int(os.getenv("AGENTSHIELD_SEED", defaults.seed)),
            num_ctx=int(os.getenv("AGENTSHIELD_NUM_CTX", defaults.num_ctx)),
            max_steps=int(os.getenv("AGENTSHIELD_MAX_STEPS", defaults.max_steps)),
            runs_dir=Path(os.getenv("AGENTSHIELD_RUNS_DIR", defaults.runs_dir)),
        )

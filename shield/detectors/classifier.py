"""Layer 2: a fine-tuned multilingual classifier (xlm-roberta-base).

Training happens off-box on a GPU (Colab/Kaggle) with ``shield.detectors.train_classifier``;
this module is the inference wrapper. If transformers/torch or a trained model are missing,
the detector reports ``available = False`` and returns a neutral signal, so the rest of the
pipeline still runs.
"""

from __future__ import annotations

from pathlib import Path

from agents.config import REPO_ROOT
from shield.detectors.base import Context, Signal, timed
from shield.preprocess.types import Chunk

DEFAULT_MODEL_DIR = REPO_ROOT / "models" / "xlmr-injection"


class ClassifierDetector:
    name = "classifier"

    def __init__(self, model_dir: Path | str = DEFAULT_MODEL_DIR, threshold: float = 0.5, max_length: int = 256) -> None:
        self.model_dir = Path(model_dir)
        self.threshold = threshold
        self.max_length = max_length
        self._model = None
        self._tokenizer = None
        self._torch = None
        self._load_error = ""
        self._try_load()

    def _try_load(self) -> None:
        if not self.model_dir.exists():
            self._load_error = f"no trained model at {self.model_dir} (run shield.detectors.train_classifier)"
            return
        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            self._tokenizer = AutoTokenizer.from_pretrained(self.model_dir)
            self._model = AutoModelForSequenceClassification.from_pretrained(self.model_dir)
            self._model.eval()
            self._torch = torch
        except Exception as error:  # noqa: BLE001 - any load failure degrades gracefully
            self._load_error = f"could not load classifier: {error}"

    @property
    def available(self) -> bool:
        return self._model is not None

    def score(self, chunk: Chunk, context: Context) -> Signal:
        def run() -> Signal:
            if not self.available:
                return Signal(0.0, self._load_error, label="uncertain", layer="L2")
            torch = self._torch
            inputs = self._tokenizer(
                chunk.text, truncation=True, max_length=self.max_length, return_tensors="pt"
            )
            with torch.no_grad():
                logits = self._model(**inputs).logits[0]
                prob_attack = torch.softmax(logits, dim=-1)[1].item()
            return Signal.from_score(
                prob_attack, f"classifier P(attack)={prob_attack:.2f}", layer="L2", threshold=self.threshold
            )

        return timed(run)

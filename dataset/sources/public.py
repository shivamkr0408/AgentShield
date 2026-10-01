"""Ingest public prompt-injection datasets from the Hugging Face Hub.

This is where the bulk of attack samples legitimately comes from: existing, published,
licensed corpora. Running it needs ``pip install datasets`` and network access, and the
output is written under ``data/generated/`` (git-ignored), never committed.

Each entry in ``REGISTRY`` maps a Hub dataset to our schema. Add a new public source by
appending a ``HFSource`` here; no new code is needed. Most public sets only mark a sample
as injection/benign without a fine-grained technique, so attacks land in the "unknown"
category and are refined later by the labelling task.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field

from dataset.schema import Record


@dataclass(frozen=True)
class HFSource:
    name: str              # short id used in Record.source, e.g. "deepset"
    hf_path: str           # Hugging Face dataset path
    text_column: str
    label_column: str
    # Maps the source's label values to our labels. Values not listed are skipped.
    label_map: dict[str, str]
    split: str = "train"
    language: str = "en"
    license: str = "see dataset card"
    config: str | None = None
    note: str = ""


# A starting registry of well-known, openly available injection datasets. Verify each
# dataset's license and current schema (column names, label values) before relying on it;
# Hub datasets change. Licenses here are reminders, not legal advice.
REGISTRY: list[HFSource] = [
    HFSource(
        name="deepset",
        hf_path="deepset/prompt-injections",
        text_column="text",
        label_column="label",
        label_map={"1": "attack", "0": "benign", "1.0": "attack", "0.0": "benign"},
        license="unknown - check dataset card",
        note="English/German injections and benign prompts.",
    ),
    HFSource(
        name="safeguard",
        hf_path="xTRam1/safe-guard-prompt-injection",
        text_column="text",
        label_column="label",
        label_map={"1": "attack", "0": "benign"},
        license="check dataset card",
    ),
    HFSource(
        name="jailbreak",
        hf_path="jackhhao/jailbreak-classification",
        text_column="prompt",
        label_column="type",
        label_map={"jailbreak": "attack", "benign": "benign"},
        license="check dataset card",
        note="Direct jailbreak prompts; useful as a related-but-distinct class.",
    ),
]

# Benchmark suites ship attacks as code or templates rather than a flat labelled file, so
# they get a dedicated adapter each (left as stubs with pointers for the data team).
BENCHMARK_SUITES: dict[str, str] = {
    "bipia": "github.com/microsoft/BIPIA - attack templates under bipia/; join with contexts.",
    "injecagent": "github.com/uiuc-kang-lab/InjecAgent - attacker cases in data/*.json.",
    "agentdojo": "pip install agentdojo - iterate attacks via its task suites.",
}


def load_hf_source(source: HFSource, limit: int | None = None) -> Iterator[Record]:
    """Yield normalized records from one Hugging Face source. Requires the ``datasets`` package."""
    try:
        from datasets import load_dataset
    except ImportError as error:
        raise RuntimeError("Install the optional dependency first: pip install datasets") from error

    dataset = load_dataset(source.hf_path, source.config, split=source.split)
    for index, row in enumerate(dataset):
        if limit is not None and index >= limit:
            break
        label = source.label_map.get(str(row.get(source.label_column)).strip())
        text = str(row.get(source.text_column, "")).strip()
        if label is None or not text:
            continue
        yield Record(
            text=text,
            label=label,
            category="unknown" if label == "attack" else "benign_plain",
            language=source.language,
            source=f"public:{source.name}",
            goal="unknown" if label == "attack" else None,
            meta={"hf_path": source.hf_path, "license": source.license},
        )


def available_sources() -> list[str]:
    return [source.name for source in REGISTRY]

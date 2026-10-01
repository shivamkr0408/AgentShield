"""Download public injection datasets into data/generated/public/ (git-ignored).

    python -m dataset.ingest --list
    python -m dataset.ingest --source deepset --limit 2000
    python -m dataset.ingest --all

Needs the optional dependency: pip install datasets
"""

from __future__ import annotations

import argparse

from agents.config import REPO_ROOT
from dataset.schema import write_jsonl
from dataset.sources.public import BENCHMARK_SUITES, REGISTRY, load_hf_source

OUT_DIR = REPO_ROOT / "data" / "generated" / "public"


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest public prompt-injection datasets.")
    parser.add_argument("--source", help="Registry source name (see --list).")
    parser.add_argument("--all", action="store_true", help="Ingest every registry source.")
    parser.add_argument("--limit", type=int, help="Max rows per source.")
    parser.add_argument("--list", action="store_true", help="List known sources and exit.")
    args = parser.parse_args()

    if args.list or not (args.source or args.all):
        print("Hugging Face sources (python -m dataset.ingest --source <name>):")
        for source in REGISTRY:
            print(f"  {source.name:<12} {source.hf_path:<42} license: {source.license}")
        print("\nBenchmark suites (need a dedicated adapter; pointers for the data team):")
        for name, pointer in BENCHMARK_SUITES.items():
            print(f"  {name:<12} {pointer}")
        return

    chosen = REGISTRY if args.all else [s for s in REGISTRY if s.name == args.source]
    if not chosen:
        raise SystemExit(f"Unknown source {args.source!r}. Use --list to see the options.")

    for source in chosen:
        print(f"Ingesting {source.name} ({source.hf_path}) ...", flush=True)
        try:
            records = list(load_hf_source(source, limit=args.limit))
        except Exception as error:  # network, missing dep, or a changed schema
            print(f"  skipped: {error}")
            continue
        written = write_jsonl(records, OUT_DIR / f"{source.name}.jsonl")
        print(f"  wrote {written} records to {(OUT_DIR / f'{source.name}.jsonl').relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()

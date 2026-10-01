# Public data sources

The bulk of the attack class comes from existing, published datasets rather than newly
authored payloads. Ingest them with `python -m dataset.ingest` (needs `pip install datasets`
and network); output lands in `data/generated/` and is never committed. **Check each
dataset's licence and current schema before use** — Hub datasets change column names and
labels over time, and the notes below are reminders, not legal advice.

## Hugging Face sources (in `dataset/sources/public.py`)

| Name | Path | Content | Licence |
|---|---|---|---|
| `deepset` | `deepset/prompt-injections` | English/German injections + benign | check card |
| `safeguard` | `xTRam1/safe-guard-prompt-injection` | injection vs. benign | check card |
| `jailbreak` | `jackhhao/jailbreak-classification` | direct jailbreak vs. benign | check card |

Add a source by appending an `HFSource` to the registry — no new code required.

## Benchmark suites (need a dedicated adapter)

| Name | Where | Notes |
|---|---|---|
| BIPIA | `github.com/microsoft/BIPIA` | attack templates joined with contexts |
| InjecAgent | `github.com/uiuc-kang-lab/InjecAgent` | attacker cases in `data/*.json` |
| AgentDojo | `pip install agentdojo` | iterate attacks via its task suites |

These overlap with AgentShield's own agent benchmark (Phase 7); here we use only their
attack *strings* as detector training/eval data.

## Labelling note

Public samples usually carry only a binary injection/benign label, so attacks ingested this
way land in the `unknown` technique category. A later labelling pass maps them onto the
taxonomy; the human-authored seeds and multilingual set are categorized from the start.

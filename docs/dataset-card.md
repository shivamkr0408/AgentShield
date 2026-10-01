# Dataset card: AgentShield Multilingual Prompt-Injection Corpus

A labeled corpus for training and evaluating prompt-injection detectors, with a distinctive
human-authored Hindi, Tamil, Hinglish, and Tanglish component. Phase 2 deliverable.

> **Status.** The framework, the benign hard-negative controls, the public-data adapters,
> and the annotation harness are in place. The attack class is populated by ingesting public
> corpora and by the human annotation process (see below); it is not machine-generated in
> bulk. Target size once populated: ~5,000–10,000 labeled samples.

## Intended use

- **In scope:** training and evaluating detectors and the AgentShield defense layers;
  measuring detection across languages and false positives on benign text.
- **Out of scope:** attacking any real system or person. Every sample is security test
  material for the AgentShield sandbox.

## Composition

Each sample is a JSON object (schema in `dataset/schema.py`):

| Field | Meaning |
|---|---|
| `id` | `<source>:<hash>`, stable and derived from the text |
| `text` | the sample |
| `label` | `attack` or `benign` |
| `category` | technique (attacks) or benign subtype — see `dataset/taxonomy.py` |
| `language` | `en`, `hi`, `ta`, `hi-Latn`, `ta-Latn` |
| `script` | `latin`, `devanagari`, `tamil`, or `mixed` (auto-detected, validated) |
| `source` | `public:<name>`, `human:multilingual`, `benign:authored`, or `seed` |
| `goal` | attacks only: `action_hijack`, `data_exfiltration`, `prompt_leak`, `misinformation`, `denial` |
| `parent_id` | links a translated/code-mixed sample to its English seed |
| `meta` | provenance, licence, review flags |

**Attack categories:** instruction_override, role_hijacking, hidden_html, encoded_text,
invisible_chars, homoglyph, image_text (transcribed), and `unknown` for uncategorized
public data.
**Benign categories:** benign_plain, and the hard negatives benign_instructional,
benign_quoted, benign_technical.

## Sources

- **Public corpora** (`data/sources.md`): the bulk of the attack class, ingested under their
  own licences. Verify each licence before redistribution.
- **Human-authored multilingual** (`data/multilingual/`): written and reviewed by fluent
  speakers per `GUIDELINES.md`. Two-person review; inter-annotator agreement tracked on a
  200-sample shared set.
- **Authored benign hard negatives** (`data/benign/`): false-positive controls.

## Splits

Built by `python -m dataset.build`, written to `data/generated/splits/` (git-ignored):

- **train / val / test** — a 70/15/15 split, stratified by (label, category, language) so
  each split mirrors the whole. Deterministic given `--seed`.
- **heldout** — one attack category (default `encoded_text`) removed from train and val
  entirely, so generalization to an unseen technique can be measured on its own.

Exact-text duplicates are removed before splitting; invisible-character and homoglyph
variants are byte-distinct and kept on purpose. `stats.json` records the per-split breakdown.

## Reproducing

```powershell
python -m dataset.ingest --all                 # optional: public data -> data/generated/
python -m dataset.from_annotations batch.csv --out data/multilingual/batch1.jsonl
python -m dataset.validate
python -m dataset.build --heldout-category encoded_text --seed 7
```

## Limitations and ethics

- Language coverage is skewed toward English until the human batches land; per-language
  counts are in `stats.json`, and small per-language groups give noisy estimates.
- Public attacks are mostly direct-injection/jailbreak text, which differs from the indirect,
  tool-mediated attacks the agent benchmark (Phase 7) measures. The two are complementary.
- Multilingual rows carry `needs_review` until a native speaker signs off; do not report on
  unreviewed data.
- Release with a responsible-use note. The corpus is for building defenses; it must not be
  used to attack third-party systems.

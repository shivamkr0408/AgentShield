---
license: cc-by-4.0
language:
  - en
  - hi
  - ta
task_categories:
  - text-classification
tags:
  - prompt-injection
  - llm-security
  - ai-safety
  - multilingual
  - code-switching
pretty_name: AgentShield Multilingual Prompt-Injection Corpus
size_categories:
  - 1K<n<10K
---

# AgentShield Multilingual Prompt-Injection Corpus

> Upload this file as `README.md` to the Hugging Face dataset repo
> `shivamkr0408/agentshield-multilingual-injection`, alongside `train.jsonl`,
> `validation.jsonl`, and `test.jsonl` produced by `python -m dataset.build`.

A labelled corpus for training and evaluating prompt-injection detectors for LLM agents, with a
distinctive human-authored **Hindi, Tamil, Hinglish, and Tanglish** component and benign hard
negatives. Part of the [AgentShield](https://github.com/shivamkr0408/AgentShield) project.

## Purpose

Existing agent-injection benchmarks are English-only. This corpus measures detection across
languages and scripts, and false positives on benign imperative text.

## Languages

English (`en`), Hindi (`hi`, Devanagari), Tamil (`ta`), Hinglish (`hi-Latn`), Tanglish (`ta-Latn`).

## Label schema

Each row (JSONL):

| field | meaning |
|---|---|
| `id` | stable id `<source>:<hash>` |
| `text` | the sample |
| `label` | `attack` or `benign` |
| `category` | attack technique or benign subtype |
| `language` / `script` | e.g. `hi` / `devanagari` |
| `source` | provenance (`public:…`, `human:multilingual`, `benign:authored`) |
| `goal` | attacks only: action_hijack, data_exfiltration, prompt_leak, misinformation, denial |
| `parent_id` | links a translated sample to its English seed |

Attack categories: instruction_override, role_hijacking, hidden_html, encoded_text,
invisible_chars, homoglyph, image_text, unknown. Benign: plain, instructional, quoted, technical.

## Splits

70/15/15 train/validation/test, stratified by (label, category, language), with one attack
category held out entirely for a generalization test. Size per split: `[PENDING]` (regenerate
with `python -m dataset.build`; see `data/generated/splits/stats.json`).

## Collection

Public attacks are ingested from openly licensed sources (see the repo's `data/sources.md`).
The multilingual set is human-authored and double-reviewed (`data/multilingual/GUIDELINES.md`).
Benign hard negatives are authored to stress false positives. Full details:
[DATASHEET](https://github.com/shivamkr0408/AgentShield/blob/main/docs/DATASHEET.md).

## License

**CC BY 4.0.** Please cite the AgentShield project.

## Limitations & ethics

Language coverage is skewed toward English until the human batches land. This dataset is for
**defensive research only** — building and evaluating defenses, not attacking real systems. See
the [ethics statement](https://github.com/shivamkr0408/AgentShield/blob/main/docs/ETHICS.md).

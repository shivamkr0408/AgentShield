# Datasheet: AgentShield Multilingual Prompt-Injection Corpus

Following Gebru et al., *Datasheets for Datasets*. This complements the dataset card
(`docs/dataset-card.md`); where numbers are not yet final they are marked `[PENDING]`.

## Motivation

- **Why created?** Existing agent-injection benchmarks (AgentDojo, InjecAgent, BIPIA) are
  English-only. This corpus adds Hindi, Tamil, and code-mixed Hinglish/Tanglish, plus benign
  hard negatives, to measure multilingual detection and false positives.
- **Who created it?** The AgentShield final-year project team, with native/fluent-speaker
  annotators for the multilingual set.

## Composition

- **Instances:** text samples, each labelled attack or benign with a technique/category,
  language, script, source, and (for attacks) a goal. Schema in `dataset/schema.py`.
- **Counts:** currently 41 committed benign hard negatives across en/hi/ta/hi-Latn/ta-Latn;
  the attack class is populated by public ingestion and human annotation — total target
  ~5–10k `[PENDING]`.
- **Languages:** English, Hindi (Devanagari), Tamil, Hinglish (hi-Latn), Tanglish (ta-Latn).
- **Labels:** `attack`/`benign`; attack categories = instruction_override, role_hijacking,
  hidden_html, encoded_text, invisible_chars, homoglyph, image_text, unknown; benign categories =
  plain, instructional, quoted, technical.
- **Sensitive data?** None. No real personal data, credentials, or identifiers. Sandbox secrets
  are fake placeholders.

## Collection

- **Public attacks:** ingested from openly licensed Hugging Face datasets via
  `dataset/sources/public.py` (see `data/sources.md`); licenses retained per source.
- **Human multilingual:** authored and double-reviewed per `data/multilingual/GUIDELINES.md`;
  inter-annotator agreement tracked on a 200-sample shared set.
- **Benign hard negatives:** authored (recipes, manuals, quoted text, code) to stress false
  positives.
- **Generated/derived data** lives in `data/generated/` and is not committed.

## Preprocessing / splits

- Deduplicated on exact text (obfuscation variants kept, being byte-distinct).
- 70/15/15 train/val/test, stratified by (label, category, language), with one attack category
  (`encoded_text` by default) held out entirely for a generalization test. Built by
  `python -m dataset.build`.

## Uses

- **Intended:** training/evaluating prompt-injection detectors and the AgentShield layers.
- **Not intended:** attacking any real system; any use outside defensive research.

## Distribution

- Released on Hugging Face Datasets under **CC BY 4.0**, with a responsible-use note and this
  datasheet.

## Maintenance

- Maintained in the GitHub repository; issues and corrections via GitHub. Versioned with the
  code; regenerated with `python -m dataset.build`.

## Limitations

- Language coverage is skewed toward English until the human batches land.
- Public attacks are mostly direct-injection/jailbreak text (category `unknown`), complementary
  to the indirect, tool-mediated attacks the agent benchmark measures.

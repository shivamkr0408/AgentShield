# Multilingual annotation guidelines

This is AgentShield's distinctive contribution: a Hindi, Tamil, and code-mixed (Hinglish,
Tanglish) set of prompt-injection and benign samples, **written and reviewed by people**,
not machine-translated. Native and fluent speakers author the samples; a second speaker
reviews each one before it enters the dataset.

## Why human-authored

Machine translation flattens the way attacks actually appear in these languages: it misses
code-switching, transliteration, local idiom, and script mixing. Those are exactly the
cases an English-trained detector is expected to miss, so they must be written by people
who use the language.

## Scope and ethics

- Samples exist only to **train and test a defender** in the AgentShield sandbox. They
  target the mock agent and its fake tools, never any real system or person.
- Do not include real secrets, real personal data, or real account numbers. Use the
  obviously-fake `.test` placeholders from the sandbox.
- Keep payloads at the level already documented in the public literature and benchmarks.
  The goal is coverage of known techniques in new languages, not novel capability.
- The dataset ships under a responsible-use note (see the dataset card). Treat it as
  security test material, and store work-in-progress in the shared private workspace.

## The CSV columns (`template.csv`)

| Column | Meaning |
|---|---|
| `seed_id` | The English seed this is based on, e.g. `OVR-003`, or a new id. Lets us pair languages. |
| `category` | One attack technique or benign category (see below). |
| `goal` | For attacks only: `action_hijack`, `data_exfiltration`, `prompt_leak`, `misinformation`, or `denial`. |
| `language` | `hi`, `ta`, `hi-Latn` (Hinglish), or `ta-Latn` (Tanglish). |
| `text` | The sample itself, in that language. |
| `author` | Who wrote it. |
| `reviewer` | The second speaker who checked it. |
| `review_status` | `draft`, `needs_fix`, or `approved`. Only `approved` rows are exported. |
| `notes` | Anything the reviewer should know. |

Attack categories: `instruction_override`, `role_hijacking`, `hidden_html`,
`encoded_text`, `invisible_chars`, `homoglyph`, `image_text`.
Benign categories: `benign_plain`, `benign_instructional`, `benign_quoted`, `benign_technical`.

Write benign rows too, especially hard negatives in each language (recipes, manuals,
quoted text that uses "instruction" words). They anchor the false-positive rate per language.

## Process

1. Copy `template.csv` for your batch and delete the example row.
2. For each English seed, write the same idea naturally in your language. Aim for parallel
   coverage across the four language tags so splits stay balanced.
3. A second speaker sets `review_status` to `approved` (or `needs_fix` with a note).
4. Track inter-annotator agreement on a shared sample of 200 rows.
5. Export the approved rows:
   ```powershell
   python -m dataset.from_annotations my_batch.csv --out data/multilingual/batch1.jsonl
   ```
6. Run `python -m dataset.validate`, then rebuild with `python -m dataset.build`.

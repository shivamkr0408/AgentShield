# Attack seeds

English seed attacks, one JSONL record per sample, in the schema from `dataset/schema.py`
(`text`, `label: "attack"`, `category`, `goal`, ...). Seeds serve two purposes:

1. They are the English half of the dataset's attack class.
2. Each seed's `id` becomes the `parent_id` of the human-authored Hindi/Tamil/Hinglish/
   Tanglish versions, so the multilingual samples can be paired back to their source idea.

## Where seeds come from

Seeds are **not** machine-authored in bulk. They come from:

- **Public corpora**, ingested with `python -m dataset.ingest` into `data/generated/`
  (git-ignored). These supply volume for detector training; most arrive in the `unknown`
  category and are refined by a labelling pass.
- **The benchmark suites** (BIPIA, InjecAgent, AgentDojo) via their dedicated adapters.
- **Human authors**, who write categorized English seeds covering each technique in
  `dataset/taxonomy.py`, reviewed the same way as the multilingual set.

Commit only categorized, reviewed seeds here. Keep raw ingested dumps in `data/generated/`.
Use the obviously-fake `.test` placeholders from the sandbox for any attacker destination,
and never include real secrets or personal data.

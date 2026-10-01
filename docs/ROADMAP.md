# AgentShield Roadmap

**AgentShield: Provenance-Aware Defense Against Multilingual Prompt Injection in LLM Agents**

15 weeks, team of 2–4. Some phases overlap on purpose so that no one is blocked while waiting on another phase.

| Week | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P0 Foundation | ■ | | | | | | | | | | | | | | |
| P1 Agents and tools | | ■ | ■ | | | | | | | | | | | | |
| P2 Multilingual dataset | | | ■ | ■ | ■ | | | | | | | | | | |
| P3 Preprocess and detectors | | | | | ■ | ■ | ■ | | | | | | | | |
| P4 Canary, taint, firewall | | | | | | | ■ | ■ | ■ | | | | | | |
| P5 Adaptive attacker | | | | | | | | | ■ | ■ | ■ | | | | |
| P6 API and live dashboard | | | | | | | | ■ | ■ | ■ | ■ | ■ | | | |
| P7 Evaluation and ablations | | | | | | | | | | | ■ | ■ | ■ | | |
| P8 Write-up and submission | | | | | | | | | | | | | ■ | ■ | ■ |

---

## Phase 0: Foundation (Week 1)

**Goal:** environment ready and the problem understood.

- Read the core papers on indirect prompt injection, AgentDojo, InjecAgent, BIPIA, and the dual-LLM pattern
- Install Python 3.11, Git, Ollama with a local model (Llama 3.1 8B or Qwen 2.5 7B), and Node.js
- Create the repository layout

**Deliverable:** working setup and the two-page literature summary ([literature-summary.md](literature-summary.md)).

---

## Phase 1: Sandboxed Test Agent (Weeks 2–3)

**Goal:** a realistic agent you can safely attack, to use as the baseline.

- Build the agent with LangGraph and a local LLM through Ollama (`agents/agent.py`, `agents/llm.py`).
- **Mock tools only** (`agents/tools.py`). Nothing touches real accounts or the internet:
  - a JSON inbox: `list_emails`, `read_email`, `search_emails`
  - a local Flask test website at `http://acme.test`, read with `browse_web` (`agents/website.py`)
  - a sandbox file folder: `list_files`, `read_file`, `write_file`
  - a mock outbox: `send_email`
  - a mock HTTP endpoint: `http_post`, plus any non-intranet URL, which is recorded and never sent
- **Fake secrets** in `private/` (API keys, a database password, payroll bank details) serve as exfiltration targets. Their values are listed in `agents/world/manifest.json`.
- **25 normal tasks** (`data/tasks/benign_tasks.json`), each with automatic checks. Every task also checks for side effects nobody asked for.
- **One hook point** (`agents/hooks.py`): `ToolGateway` sends every proposed call to `ToolHook.before_call` and every piece of tool output to `ToolHook.after_result`. AgentShield plugs in here later.
- **Injection slots** (`agents/sandbox.py`): a scenario places a payload in an email, a web page (optionally hidden) or a file. The format is in `data/attacks/README.md`.
- Each run writes a JSONL trace to `runs/`. The dashboard will stream the same events later.

**Deliverable:** an agent that completes normal tasks and can be shown to fail against injected content. Record this as the "before" demo:

```powershell
python -m eval.run benign
python -m eval.run injections --scenarios data/attacks/before_demo.json --verbose
```

---

## Phase 2: Multilingual Attack and Benign Dataset (Weeks 3–4)

**Goal:** labeled data for training and testing. Publishable on its own.

- **Collect public datasets** from Hugging Face and the benchmark suites with
  `python -m dataset.ingest` (adapters in `dataset/sources/public.py`; list in `data/sources.md`).
  Output is git-ignored under `data/generated/`.
- **Organize attacks by category** (`dataset/taxonomy.py`): instruction override, role
  hijacking, hidden HTML, encoded text, invisible characters, look-alike letters (homoglyphs),
  image-embedded text (stored as its transcription), plus a `data_exfiltration` goal that cuts
  across techniques.
- **Unique contribution: a human-authored Hindi, Tamil, Hinglish, and Tanglish set**, written
  and reviewed by people, not machine-translated. The annotation harness is in
  `data/multilingual/` (`template.csv`, `GUIDELINES.md`); approved rows are exported with
  `python -m dataset.from_annotations`.
- **Benign content with hard negatives** (`data/benign/hard_negatives.jsonl`): manuals, recipes,
  quoted text, and code that use "instruction" and imperative language, to keep the
  false-positive rate honest.
- **Splits** (`python -m dataset.build`): a 70/15/15 stratified train/val/test split plus one
  attack category held out entirely, to test generalization.
- **Dataset card** (`docs/dataset-card.md`) documents schema, sources, licences, splits, and
  a responsible-use note.

**Division of labor:** the pipeline, the benign controls, the public-data adapters, and the
annotation harness are built and tested. The attack class is populated by ingesting public
corpora and by the human annotation process — attack payloads are not machine-authored in bulk.

**Deliverable:** about 5,000–10,000 labeled samples once the public ingestion and the human
batches land.

---

## Phase 3: Preprocessing (Week 5)

**Goal:** expose everything attackers try to hide.

- **Visible vs. hidden HTML** separated, recording that hiding occurred and how — `display:none`,
  `visibility:hidden`, `hidden`, `aria-hidden`, zero font-size, off-screen, white text, and
  comments (`shield/preprocess/html_extract.py`).
- **De-obfuscation** (`shield/preprocess/normalize.py`, `encodings.py`): decode base64, hex,
  URL-encoding, and ROT13; apply Unicode NFKC; strip invisible characters (keeping Indic
  ZWNJ/ZWJ); map look-alike letters to Latin.
- **OCR** (`shield/preprocess/ocr.py`): Tesseract on images and PDF pages, as an optional
  dependency that degrades cleanly when the binary is absent.
- **Chunking with metadata** (`shield/preprocess/pipeline.py`): each `Chunk` carries source,
  origin, and the hidden / encoded / homoglyph / invisible flags that every later layer reads.

**Deliverable:** `shield/preprocess/` with a unit test per hiding technique (`tests/test_preprocess.py`).

---

## Phase 4: Detection Layers (Weeks 5–7)

**Goal:** the three-layer detector. Every layer exposes `score(chunk, context) -> Signal`,
and a `Signal` unpacks to `(score, reason)`.

- **Layer 1 — rule filter** (`shield/detectors/rules.py`): precompiled multilingual trigger
  patterns (en, hi, ta, Hinglish, Tanglish) plus structural signals (imperatives aimed at the
  assistant, tool names inside data, secrets next to URLs) and the obfuscation flags from
  preprocessing. Measured at ~0.1 ms per chunk, well under the 5 ms budget.
- **Layer 2 — ML classifier** (`shield/detectors/classifier.py`, `train_classifier.py`):
  fine-tune xlm-roberta-base on the Phase 2 dataset using Colab/Kaggle GPUs. The training
  script reports precision/recall/F1 per category and per language; the inference wrapper
  degrades gracefully when no model is present.
- **Layer 3 — intent check** (`shield/detectors/intent.py`): compares the user's task with what
  the content asks the agent to do, using a small local LLM judge (and optional embedding
  divergence). Returns a score and a one-line reason. The judge is injectable for testing.
- **Metrics + harness** (`shield/detectors/metrics.py`, `eval/detect_eval.py`): per-layer,
  per-language, per-category precision/recall/F1/FPR with latency, saved to `runs/detectors/`.

**Deliverable:** three tested detectors (`tests/test_detectors.py`) and per-layer metrics.
Early signal on the benign hard negatives: Layer 1 alone shows ~27% FPR on quoted-injection
text, which is exactly what Layers 2 and 3 are there to reduce.

---

## Phase 5: Canary Tokens and Taint Tracking (Weeks 8–9)

**Goal:** the core research contributions. Both plug into the single Phase 1 hook.

**Canary tokens** (`shield/canary/`):
- A fresh random token per session, placed in the system prompt (via the agent's
  `system_suffix`) and seeded into the sandbox's sensitive files; pre-existing planted secrets
  are also registered as tripwires.
- Every outgoing tool call is scanned; a hit blocks the action and traces back to where the
  token lived (which file or the prompt) and the last external source read.
- Tokens are long and random, so natural false positives are astronomically unlikely.

**Taint tracking** (`shield/taint/`):
- Labels data by origin — USER, PRIVATE, or EXTERNAL — from each tool result's source and
  content (a planted secret anywhere makes it PRIVATE).
- Remembers which labels have entered the session's context.
- Policy: a PRIVATE value heading to an EXTERNAL destination is blocked; the PRIVATE+EXTERNAL
  combination without the literal value is sent for human approval; internal destinations are
  allowed.

**Deliverable:** both modules integrated into the firewall, with tests showing they catch
exfiltration that the content detectors miss — e.g. a benign-looking page that drives the
agent to email a secret out is stopped by the canary/taint check, not by any trigger word.

---

## Phase 6: Risk Fusion and Action Firewall (Week 10)

**Goal:** combine all signals into decisions.

- **Risk fusion** (`shield/scoring.py`, `eval/fit_fusion.py`): a logistic-regression fuser over
  the layer scores (rules, classifier, intent, canary, taint). Weights are learned on the
  validation split and `explain()` reports each layer's contribution for the write-up. Hand-set
  defaults let the firewall run before training, and are tuned so any single high-confidence
  layer still crosses the sanitize threshold (important while only Layer 1 is available).
- **Three content outcomes** (`shield/firewall/sanitize.py`): allow, **sanitize** (drop the
  flagged sentences and wrap the rest as untrusted data), or block (withhold high-risk content).
- **Action firewall** (`shield/firewall/`): per-task permissions in YAML (`config/firewall.yaml`),
  canary and taint checks before any tool runs, and human approval for sensitive or
  taint-flagged actions.
- **Fail-safe:** approval requests run under a timeout; anything unanswered is denied.

**Deliverable:** the full pipeline working end to end — `python -m eval.run injections
--scenarios <file> --defense full`. Verified on a scripted exfiltration run: the secret email
is blocked while a benign internal reply still succeeds.

---

## Phase 7: Backend API (Week 11)

**Goal:** a live backend the dashboard and other agents can use.

- **FastAPI endpoints** (`api/main.py`): `POST /scan`, `POST /check_action`, `GET /events`,
  `GET /incidents` and `GET /incidents/{id}` (history + replay), `GET /approvals` with
  `POST /approvals/{id}/approve|deny`, `GET /policy` and `PUT /policy` (change thresholds and
  layers live), `GET /stats`, and `POST /incidents` to scope a session.
- **WebSocket** `/ws/events` pushes every new decision to connected dashboards instantly
  (`api/events.py`).
- **SQLite via SQLAlchemy** (`api/db.py`) stores events, incidents, approvals, and the policy.
- **SDK** (`api/sdk.py`): `AgentShield.wrap(run_agent)` returns a shielded agent runner; an
  optional `store_url` streams its decisions into the same store the dashboard reads.

**Deliverable:** a running API with interactive docs at `/docs` and an installable package.
Verified: `/scan` pushes a live event over the WebSocket; the built dashboard is served at `/`.

---

## Phase 8: Live, Responsive Dashboard (Weeks 12–13)

**Goal:** a real-time web app that works on phones, tablets, and laptops.

- **Stack:** React + Vite, Recharts for charts, a native reconnecting WebSocket client, and a
  self-contained CSS design system (tokens, responsive grid, dark/light) in place of Tailwind
  for build reliability; the structure stays utility-class portable.
- **Pages** (`web/src/pages.jsx`): Overview (live stat cards, traffic-and-threats chart, which
  layer stopped each attack, attack mix, streaming feed); Incidents (list + step-by-step replay
  with provenance tags, flagged text, per-layer scores); Approvals (paused actions, the data
  chain, approve/deny, and a countdown to auto-deny); Playground (paste text, scan with the real
  `/scan`, see the verdict and highlights); Policies (threshold sliders and layer toggles applied
  live).
- **Live behavior** (`web/src/main.jsx`): initial state from the API, then WebSocket updates with
  no refresh; toast notifications for blocks and new approvals; auto-reconnect with a connection
  badge.
- **Any device:** sidebar on desktop, icon rail on tablet, bottom tab bar on phone; responsive
  grids; `ResponsiveContainer` charts; 44px+ touch targets; safe-area padding; light/dark
  following the device; number keys 1–5 switch pages for the demo.

**Deliverable:** the dashboard updating in real time as the agent runs. One process serves both
API and UI; `--host 0.0.0.0` makes it reachable from a phone, tablet, and laptop at once.

---

## Phase 9: Adaptive Attacker and Evaluation (Weeks 13–14)

**Goal:** prove the defense works and holds up.

- **Adaptive attacker** (`eval/attacker/`): starting from dataset seed attacks, an evolutionary
  loop mutates them, tests them against a target (detector or the fused shield), reads back
  feedback shaped by the threat model (black / gray / white box), and keeps the most evasive
  variants under a query budget. Mechanical operators (base64/hex/URL/ROT13, homoglyph,
  invisible, split) are deterministic; semantic operators (paraphrase, translate, code-switch)
  call an injected LLM rewriter, so the harness never authors attack content. Successful
  evasions are collected for adversarial retraining of the classifier.
- **Metrics** (`eval/benchmark.py`, `shield/detectors/metrics.py`): attack success rate (with and
  without AgentShield), task utility, false-positive rate, latency overhead, per-language
  detection, and adaptive attack success.
- **Ablation**: remove one component at a time — rules, classifier, intent (detector-level), and
  canary, taint (action-level, with `--agent`) — and report the change in attack success.
- **Baselines** (`shield/detectors/baselines.py`): no defense, a keyword filter, and an
  open-source prompt-injection classifier, each scored on raw text so the comparison is fair.

**Deliverable:** results tables and charts, with the real numbers published to the dashboard's
Results page (`PUT /results`). Reproducible today: the preprocessor neutralizes obfuscations that
evade the keyword baseline, and canary/taint catch exfiltration the detectors miss.

---

## Phase 10: Deployment, Report, and Demo (Week 15)

**Goal:** ship it.

- **Deployment**: `docker compose up --build` brings up three services — the API, the dashboard
  (nginx), and Ollama (`docker-compose.yml`, `Dockerfile.api`, `web/Dockerfile`, `web/nginx.conf`).
  The dashboard can also be hosted on Vercel/Render with the backend on Render or a college
  server; the dataset is released on Hugging Face with its datasheet.
- **Report and paper** (`docs/report.md`): problem, related work, threat model, architecture,
  dataset, method, results, ablation, limitations, and future work — built around the canary and
  taint contributions and the multilingual dataset.
- **Viva demo script** (`docs/demo-script.md`): the unprotected agent leaking a fake secret;
  AgentShield stopping the repeat; incident replay; a Hindi/Tamil attack caught; a canary catching
  what the detectors missed; the dashboard live on a phone; the examiner trying the Playground;
  and the results/ablation charts.

**Deliverable:** a GitHub repo with a clear README and screenshots, the Docker setup, the dataset
release, the paper, and the rehearsed demo (with a recorded fallback).

---

## Suggested Roles

| Role | Owns | Phases |
|---|---|---|
| Agent and evaluation lead | `agents/`, `eval/`, benchmark adapters | 1, 5, 7 |
| Data lead | `data/`, translation pipeline, datasheet | 2, 7 |
| Shield lead | `shield/` layers, classifier training | 3, 4 |
| Platform lead | `api/`, `web/`, Docker, demo | 6, 8 |

With 2 people: one person takes agents, evaluation, and the attacker; the other takes data, shield, and the dashboard. Both write the paper.

## Targets (to check, not claims)

- Cut ASR on the held-out multilingual test set by at least 80% relative to no defense
- Keep the benign utility drop at 5 points or less, and benign FPR at 2% or less
- No language scores more than 10 points below English in TPR at 1% FPR
- Adaptive ASR stays below 20% at a 100-query budget in the gray-box setting

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Local 8B models handle tool calls poorly, so baseline utility is low | Use a fixed tool-call format and few-shot examples, and fall back to Qwen 2.5 7B. Report utility separately from security. |
| Translation quality distorts the dataset | Back-translation filtering, native-speaker spot checks, and reported agreement |
| GPU time limits classifier training | Use base-size encoders, mixed precision, and Colab or Kaggle as backup |
| Taint attribution misses paraphrased values | Report strict dual-LLM mode as an upper bound, and measure the attribution miss rate |
| Overfitting to our own attacker | Keep a held-out adaptive set and evaluate on external benchmarks |
| Live demo fails on the day | Provide a recorded video and a replay mode that reads saved event logs |

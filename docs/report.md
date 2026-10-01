# AgentShield: Provenance-Aware Defense Against Multilingual Prompt Injection in LLM Agents

**Draft report / paper skeleton.** Sections are complete in structure and method; numeric
results are marked `[FILL]` and are produced by `python -m eval.benchmark` once the dataset and
a local model are in place. Keep claims tied to the regenerated tables.

## Abstract

LLM agents that call tools are vulnerable to *indirect prompt injection*: instructions planted
in the content they read (web pages, emails, files) are followed as if they were the user's
commands. Existing defenses are evaluated almost entirely in English and are rarely tested
against an attacker who adapts to them. We present AgentShield, a layered, provenance-aware
defense that combines a de-obfuscating preprocessor, a three-layer detector (multilingual rules,
a fine-tuned multilingual classifier, and an LLM intent check), canary tokens, and origin-based
taint tracking, fused by logistic regression and enforced by a policy firewall. We also release
a multilingual indirect-injection dataset spanning English, Hindi, Tamil, and code-mixed
Hinglish/Tanglish, with benign hard negatives. On [FILL] we reduce targeted attack success from
[FILL]% to [FILL]% while keeping task utility at [FILL]% and the benign false-positive rate at
[FILL]%, and we show that canary and taint tracking catch exfiltration that content detectors
miss. Against an adaptive attacker with a [FILL]-query budget, attack success stays at [FILL]%.

## 1. Introduction

Greshake et al. [2] showed that an attacker who controls content an agent retrieves can hijack
the agent without ever talking to it. As agents gain real tools — sending email, moving money,
calling APIs — the consequence of a hijack moves from wrong text to wrong *actions*. Two gaps
motivate this work:

1. **Language.** The agent-injection benchmarks (AgentDojo [5], InjecAgent [6], BIPIA [7]) are
   English-only, yet low-resource and code-mixed inputs are known to bypass safety training
   [19, 20]. A detector trained on English is likely to miss translated, transliterated, or
   code-switched injections.
2. **Adaptivity.** Zhan et al. [18] broke eight published defenses with adaptive attacks,
   exceeding 50% attack success against every one. A defense must be evaluated against an
   attacker who knows it.

AgentShield addresses both: a multilingual dataset and detector, and a design that does not rely
on detection alone — provenance-based canary and taint checks stop harmful *actions* even when a
detector is fooled. Contributions: (i) the first multilingual indirect-injection corpus for
agents, with benign hard negatives; (ii) a layered defense fusing probabilistic detection with
deterministic provenance control; (iii) an adaptive-attacker evaluation and a full ablation;
(iv) an open, reproducible implementation with a live dashboard.

## 2. Related work

We summarize the threat, benchmarks, and defense families in `docs/literature-summary.md`.
Briefly: prompt-level defenses such as spotlighting [8] mark untrusted text; training-time
defenses (StruQ [9], SecAlign [10], Instruction Hierarchy [11]) teach a data/instruction
boundary; detection spans classifiers, known-answer checks [3, 12], and task-drift probes [13];
and system-level defenses (Dual LLM [14], CaMeL [15], FIDES [16], design patterns [17]) enforce
security outside the model via capabilities or information-flow control. AgentShield borrows the
known-answer idea for its canary layer and the information-flow idea for its taint layer, and
adds the multilingual dimension none of these measure.

## 3. Threat model

The attacker controls some content the agent will read (an email body, a web page, a file) but
cannot change the user's instruction, the system prompt, the tools, or the firewall. Their goals
are to hijack an action, exfiltrate private data, leak the system prompt, inject misinformation,
or deny service. The defender trusts the user instruction (USER) and the user's own sensitive
data (PRIVATE), and treats all retrieved content (EXTERNAL) as untrusted. Success is measured in
a sandbox (`agents/world`) with mock tools and fake secrets; no real system is involved.

## 4. Architecture

Every tool call passes through one hook (`agents/hooks.py`, `ToolGateway`). Incoming content and
outgoing actions flow through the shield:

```
 tool output ─▶ preprocess ─▶ detectors (L1,L2,L3) ─▶ fuse ─▶ sanitize/allow/block
 tool call   ─▶ canary scan ─▶ taint policy ─▶ permissions/approval ─▶ allow/block
```

The firewall (`shield/firewall/`) is the single `ToolHook` that composes all layers, and the
backend (`api/`) exposes the same logic over HTTP/WebSocket for the dashboard and the SDK
(`AgentShield.wrap`).

## 5. Dataset

A unified JSONL schema (`dataset/schema.py`) labels each sample by `label` (attack/benign),
`category` (technique), `language`, `script`, `source`, and `goal`. Attacks come from public
corpora (ingested via `dataset/sources/public.py`) and a **human-authored** Hindi/Tamil/
Hinglish/Tanglish set (`data/multilingual/`, two-person review); benign hard negatives
(`data/benign/`) are recipes, manuals, quoted text, and code that use imperative language and
must not be flagged. Splits are 70/15/15, stratified by (label, category, language), with one
attack category (`encoded_text` by default) held out entirely to test generalization. Target
size: [FILL] (~5–10k). A datasheet is in `docs/dataset-card.md`.

## 6. Method

**Preprocessing (`shield/preprocess/`).** Separates visible from hidden HTML (recording how
each region was hidden), decodes base64/hex/URL/ROT13, applies NFKC, strips invisible characters
(preserving Indic ZWNJ/ZWJ), maps homoglyphs to Latin, and optionally OCRs images and PDFs. Each
chunk carries provenance and obfuscation flags.

**Detection (`shield/detectors/`).** L1 is a fast multilingual rule filter (~0.1 ms/chunk) over
trigger phrases and structural signals. L2 is a fine-tuned `xlm-roberta-base` classifier. L3 is
an LLM intent check that compares the user's task with what the content asks the agent to do.
All implement `score(chunk, context) -> Signal`.

**Canary tokens (`shield/canary/`).** A per-session random token is placed in the system prompt
and the sensitive files; existing secrets are registered as tripwires. Any token appearing in an
outgoing call blocks it and is traced to its origin.

**Taint tracking (`shield/taint/`).** Each result is labelled USER/PRIVATE/EXTERNAL. A PRIVATE
value heading to an EXTERNAL destination is blocked; a PRIVATE+EXTERNAL context without the
literal value requires human approval.

**Fusion and firewall (`shield/scoring.py`, `shield/firewall/`).** A logistic-regression fuser
(weights learned on validation data, `eval/fit_fusion.py`) combines the layer scores; the
firewall then allows, sanitizes, or blocks content, and allows, blocks, or requests approval for
actions, with a fail-safe timeout.

## 7. Experimental setup

Models: [FILL] (e.g., Qwen2.5-7B, Llama-3.1-8B) via Ollama, fixed seed. Benchmarks: our
multilingual test and held-out splits; AgentDojo, InjecAgent, and a BIPIA subset for external
validity. Baselines: no defense, a keyword filter, and an open-source injection classifier
(`shield/detectors/baselines.py`). All configs are reproducible with `python -m eval.benchmark`
and `python -m eval.run --defense full`.

## 8. Results

| Metric | No defense | Keyword | OSS classifier | **AgentShield** |
|---|---|---|---|---|
| Attack success rate | [FILL] | [FILL] | [FILL] | **[FILL]** |
| Task utility | [FILL] | — | — | **[FILL]** |
| False-positive rate | 0 | [FILL] | [FILL] | **[FILL]** |
| Latency / check | 0 | [FILL] | [FILL] | **[FILL]** |

Per-language detection (TPR at 1% FPR): [FILL] per language — the multilingual contribution.
Adaptive attacker (gray-box, [FILL]-query budget): attack success [FILL]%. The live numbers are
rendered on the dashboard's Results page (`PUT /results`).

## 9. Ablation

Removing one component at a time (`eval.benchmark` ablation for L1/L2/L3; `--agent` for canary
and taint) changes attack success by [FILL]. The headline qualitative result is reproducible
today: **canary and taint catch exfiltration that content detectors miss** — a benign-looking
page that drives the agent to email a secret is stopped by the tripwire, not by any trigger word
(`tests/test_firewall.py::test_canary_and_taint_catch_exfil_that_content_scanning_misses`). The
preprocessor neutralizes obfuscations (base64/hex/URL/homoglyph) that evade the keyword baseline
(`tests/test_attacker.py`).

## 10. Limitations

Local 8B models handle tool calls imperfectly, so utility is reported separately from security.
Taint is coarse for paraphrased values (mitigated by the approval path and reported strict-mode
upper bound). Browsing returns pre-rendered text, so the hidden/visible split is strongest when
the shield sees raw HTML. Dataset language coverage is skewed until the human batches land.

## 11. Ethics

All attacks run only against mock tools in the sandbox; secrets are fake. The dataset ships with
a responsible-use note and is intended to build defenses, not to attack third-party systems. The
adaptive attacker is a defensive evaluation tool and is confined to the sandbox.

## 12. Future work

Adversarial training on successful evasions; activation-based task-drift detection [13]; a strict
dual-LLM mode as a utility/security upper bound; and expanding language coverage.

## References

See `docs/literature-summary.md` for the full, numbered reference list ([1]–[20]).

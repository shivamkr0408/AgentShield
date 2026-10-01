# Viva questions and answers

25 likely examiner questions with short, strong answers. Keep answers to 2–4 sentences live.

### Problem & motivation
1. **What is prompt injection, and how is indirect injection different?**
   Prompt injection makes an LLM follow attacker text instead of the user. *Indirect* injection
   plants that text in content the agent retrieves (a web page, email, file), so the attacker
   never talks to the model directly — which is what makes agents dangerous.

2. **Why is this important for agents specifically?**
   Agents call tools — send email, move money, hit APIs. A hijack turns from "wrong answer" into
   a "wrong action" with real side effects, like data exfiltration.

3. **What gap does AgentShield fill?**
   Two: existing agent-injection benchmarks are English-only, and most defenses aren't tested
   against an adaptive attacker. We add multilingual coverage and a provenance layer that stops
   harmful actions even when detection fails, and we evaluate adaptively.

### Threat model
4. **What can the attacker do, and not do?**
   They control some retrieved content. They cannot change the user's instruction, the system
   prompt, the tools, or the firewall. Goals: hijack an action, exfiltrate data, leak the prompt,
   mislead, or deny service.

5. **Why trust the user but not the content?**
   The user is the principal; retrieved content is attacker-reachable. We label data USER /
   PRIVATE / EXTERNAL and enforce flow rules between them.

### Architecture & method
6. **Walk me through the pipeline.**
   Untrusted content → preprocess (de-obfuscate) → three detectors → fuse into a risk →
   allow/sanitize/block. Tool calls → canary scan → taint policy → permissions/approval →
   allow/block. One hook intercepts every tool call.

7. **What do the three detector layers do?**
   L1 is fast multilingual rules + structural signals; L2 is a fine-tuned xlm-roberta classifier;
   L3 is an LLM intent check comparing the user's task with what the content asks. They share one
   `score(chunk, context)` interface.

8. **What exactly does preprocessing catch?**
   Hidden HTML (display:none, comments), base64/hex/URL/ROT13 encodings, Unicode tricks
   (invisible characters, homoglyphs), and OCR'd text from images/PDFs — recording how each was
   hidden.

9. **How do canary tokens work?**
   A random per-session token is placed in the system prompt and the sensitive files. If it ever
   appears in an outgoing call, we block and trace it back to where it lived. Tokens are long and
   random, so false positives are astronomically unlikely.

10. **How does taint tracking work?**
    Every result is labelled by origin. A PRIVATE value heading to an EXTERNAL destination is
    blocked; a PRIVATE+EXTERNAL context without the literal value needs human approval; internal
    destinations are allowed.

11. **Why both detectors and provenance?**
    Detectors are probabilistic and can be fooled; provenance is deterministic but costs some
    utility. Together, provenance catches exfiltration the detectors miss, and detection catches
    content provenance alone wouldn't flag.

12. **How are the signals combined?**
    Logistic regression over the layer scores, with weights learned on validation data, so each
    layer's contribution is explainable. Sensible defaults let it run before training.

13. **What does the firewall actually do?**
    Three content outcomes (allow / sanitize / block) and three action outcomes (allow / approve
    / block), driven by canary, taint, and per-task YAML permissions. Unanswered approvals are
    denied after a timeout (fail-safe).

### Dataset
14. **What's novel about your dataset?**
    It's the first multilingual indirect-injection corpus for agents — Hindi, Tamil, Hinglish,
    Tanglish — human-authored and reviewed, with benign hard negatives for honest false-positive
    rates.

15. **Why hard negatives?**
    Benign text often uses imperative or "instruction" language (recipes, manuals, quoted email).
    Without them, a low false-positive rate is meaningless.

16. **How do you prevent train/test leakage and test generalization?**
    Exact-text dedup, stratified 70/15/15 splits, and one attack category held out entirely so we
    test against an unseen technique.

### Evaluation
17. **What metrics do you report?**
    Attack-success rate (with/without), task utility, false-positive rate, latency, per-language
    detection, and adaptive-attack success. [Reference the Results page/report.]

18. **What is the adaptive attacker?**
    An evolutionary loop that mutates seed attacks, reads feedback (black/gray/white-box), and
    keeps the most evasive variants under a query budget — the robustness test the literature
    says you must do.

19. **What does the ablation show?**
    Removing each layer in turn shows its contribution. Key qualitative result: without
    canary/taint, the benign-looking exfiltration gets through; the preprocessor is what lets the
    rules survive obfuscation.

20. **What are your baselines?**
    No defense, a keyword filter, and an open-source injection classifier — scored on raw text so
    the comparison is fair.

### Limitations & engineering
21. **Biggest limitation?**
    Local 8B models do tool-calling imperfectly, so we report utility separately from security;
    and taint is coarse for paraphrased values, mitigated by the approval path.

22. **Can an adaptive attacker beat it?**
    Detection can be pushed, but the provenance layer is deterministic — to exfiltrate, attacker
    data must reach an external sink, which taint/canary gate regardless of wording.

23. **Latency and practicality?**
    L1 is ~0.1 ms/chunk; L2/L3 run only when needed. The whole thing is a drop-in tool hook and
    an SDK (`AgentShield.wrap`), with a live dashboard and Docker deployment.

24. **How is this different from CaMeL / dual-LLM?**
    Those enforce security via capabilities/IFC and lose utility. We combine lightweight
    provenance (canary + taint) with multilingual detection and fusion — a different point on the
    utility/security trade-off, and the first with multilingual evaluation.

25. **What's next?**
    Adversarial training on the attacker's successful evasions, activation-based task-drift
    detection, a strict dual-LLM upper bound, and broader language coverage.

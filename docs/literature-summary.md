# Literature Summary

Phase 0 deliverable. It covers the threat, the benchmarks we will measure against, the main defense families, and the gaps that AgentShield targets. Numbers are as reported by each paper. Re-check them against the final versions before citing them in the report.

## 1. The threat: indirect prompt injection

Direct prompt injection ("ignore previous instructions...") was first studied systematically by Perez and Ribeiro [1]. Greshake et al. [2] showed the more dangerous *indirect* form. Here the attacker never talks to the model. Instead, they plant instructions in content the application retrieves, such as web pages, emails, or documents. The model then treats that data as commands. The authors demonstrated data theft, worm-like spreading, and content manipulation against real systems, including Bing Chat. Liu et al. [3] formalized prompt injection as a task-hijacking problem. They showed that a *combined* attack (escape characters, a fake task completion, and a context-ignoring instruction) outperforms each technique alone.

The root cause is that LLMs have no reliable boundary between instructions and data. Zverev et al. [4] measured this formally and found that no model they tested separates the two robustly. For agents, the impact grows from wrong text to **wrong actions**: sending email, moving money, or leaking files through tool calls.

## 2. Benchmarks

| Benchmark | Setting | Scale | What it measures | Use in AgentShield |
|---|---|---|---|---|
| **AgentDojo** [5] | Stateful tool-using agents in four suites: workspace, Slack, travel, banking | 97 user tasks, 629 security cases | Utility, utility under attack, targeted attack success rate (ASR) | Primary end-to-end benchmark, run with our local models |
| **InjecAgent** [6] | Single-turn tool-calling agents | 1,054 cases, 17 user tools, 62 attacker tools | ASR for direct-harm and data-stealing attacks | Secondary benchmark, mainly for data-exfiltration cases |
| **BIPIA** [7] | LLM applications over email, web, table, summarization, and code QA | Five task types | ASR on non-agentic retrieval-augmented tasks | Detector-level evaluation and benign utility |

Key findings: in InjecAgent, a ReAct-prompted GPT-4 agent followed injections 24% of the time, and adding a "hacking prompt" nearly doubled that rate. BIPIA found every model it evaluated vulnerable. It attributes this to two causes: models cannot tell context from instructions, and they do not know they should avoid executing instructions found in external content. **None of the three benchmarks is multilingual.** This is the gap our dataset fills.

## 3. Defense families

**Prompt-level defenses.** Spotlighting [8] marks untrusted text so the model can tell where it came from. It does this with delimiters, *datamarking* (interleaving a special token through the text), or encoding (e.g., base64). On GPT-family models it cut ASR from over 50% to under 2%. These defenses are cheap and need no training, but they rely on the model following the marking convention. Adaptive attackers can exploit that dependence.

**Training-time defenses.** StruQ [9] and SecAlign [10] fine-tune models to respect a separate data channel marked by reserved tokens. The Instruction Hierarchy [11] trains models to prefer system and user instructions over tool outputs. BIPIA's white-box defense, which uses boundary tokens and adversarial fine-tuning, pushes ASR close to zero on that benchmark. All of these require model weights and retraining, and they offer no hard guarantee.

**Detection.** Detection approaches fall into three groups:

- *Classifiers* label text as injected or benign. Examples are Meta's Prompt Guard models (multilingual mDeBERTa-based) and English-only DeBERTa detectors.
- *Known-answer detection* [3] asks a model to repeat a secret key while it processes the data. If the key goes missing, the data hijacked the instructions. DataSentinel [12] hardens this with a game-theoretic fine-tuning loop against attackers who adapt to evade detection.
- *Task-drift detection* [13] probes the model's activations before and after it reads external data.

Canary tokens of the kind used by Rebuff detect *leakage*: a secret token appears in output where it should not. Known-answer detection is the canary idea applied to *hijacking*.

**System-level, provenance-based defenses.** These treat the LLM as untrusted and enforce security outside it:

- **Dual LLM** [14]: a privileged LLM plans but never sees untrusted text. A quarantined LLM reads untrusted text, but its outputs come back only as opaque variables.
- **CaMeL** [15] extends this pattern. The privileged LLM writes a program, and a custom interpreter tracks the provenance (capabilities) of every value. Security policies are checked at each tool call. CaMeL completed 77% of AgentDojo tasks with provable security, against 84% undefended. It loses some utility, most visibly in the travel suite.
- **FIDES** [16] applies information-flow control. It attaches confidentiality and integrity labels to data, propagates them by dynamic taint tracking, and enforces policies deterministically.
- **Design Patterns** [17] lists architectural patterns, including plan-then-execute, action-selector, map-reduce, and dual LLM. Each pattern trades general capability for resistance to injection.

## 4. Why defenses still fail

**Adaptive attacks.** Zhan et al. [18] attacked eight indirect-injection defenses with adaptive attacks and achieved over 50% ASR against every one. The defenses included fine-tuned detectors, LLM-based detectors, perplexity filters, and prompt-level methods. Most of these defenses had been evaluated only on fixed attack sets. *Any claim about a detector must therefore include an adaptive-attacker evaluation.*

**Language.** Deng et al. [19] found that low-resource languages are about three times as likely as high-resource languages to elicit unsafe output. Yong et al. [20] showed that translating harmful prompts into low-resource languages bypassed GPT-4's safeguards 79% of the time on AdvBench. Both studies concern jailbreaks rather than injection. Still, they suggest that detectors trained mainly on English will miss injections that are translated, code-switched, or written in other scripts. To our knowledge, no agent-injection benchmark measures this.

## 5. Gaps AgentShield addresses

1. **Multilingual indirect injection in agents is unmeasured.** We will build a parallel attack and benign corpus across several languages and scripts. It will hold out languages and techniques for testing generalization.
2. **Detectors and provenance controls are evaluated separately.** Detectors are probabilistic, and taint tracking is deterministic but costs utility. We will combine them in one pipeline: a preprocess step, then detector layers, canary checks, a taint-aware firewall, and fused scoring. We will report an ablation for every layer.
3. **Defenses are rarely tested against an attacker who knows them.** Our adaptive attacker will have defense-aware feedback and multilingual mutation operators. We will report ASR as a function of query budget.
4. **Results are hard to inspect.** The live dashboard will show provenance, layer verdicts, and firewall decisions for every agent step.

## References

1. F. Perez, I. Ribeiro. *Ignore Previous Prompt: Attack Techniques for Language Models.* NeurIPS ML Safety Workshop, 2022. arXiv:2211.09527
2. K. Greshake et al. *Not What You've Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection.* AISec 2023. arXiv:2302.12173
3. Y. Liu et al. *Formalizing and Benchmarking Prompt Injection Attacks and Defenses.* USENIX Security 2024. arXiv:2310.12815
4. E. Zverev et al. *Can LLMs Separate Instructions From Data? And What Do We Even Mean By That?* ICLR 2025. arXiv:2403.06833
5. E. Debenedetti et al. *AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents.* NeurIPS 2024 Datasets & Benchmarks. arXiv:2406.13352
6. Q. Zhan et al. *InjecAgent: Benchmarking Indirect Prompt Injections in Tool-Integrated LLM Agents.* Findings of ACL 2024. arXiv:2403.02691
7. J. Yi et al. *Benchmarking and Defending Against Indirect Prompt Injection Attacks on Large Language Models.* KDD 2025. arXiv:2312.14197
8. K. Hines et al. *Defending Against Indirect Prompt Injection Attacks With Spotlighting.* 2024. arXiv:2403.14720
9. S. Chen et al. *StruQ: Defending Against Prompt Injection with Structured Queries.* USENIX Security 2025. arXiv:2402.06363
10. S. Chen et al. *SecAlign: Defending Against Prompt Injection with Preference Optimization.* 2024. arXiv:2410.05451
11. E. Wallace et al. *The Instruction Hierarchy: Training LLMs to Prioritize Privileged Instructions.* 2024. arXiv:2404.13208
12. Y. Liu et al. *DataSentinel: A Game-Theoretic Detection of Prompt Injection Attacks.* IEEE S&P 2025. arXiv:2504.11358
13. S. Abdelnabi et al. *Get My Drift? Catching LLM Task Drift with Activation Deltas.* SaTML 2025. arXiv:2406.00799
14. S. Willison. *The Dual LLM Pattern for Building AI Assistants That Can Resist Prompt Injection.* Blog post, April 2023.
15. E. Debenedetti et al. *Defeating Prompt Injections by Design.* SaTML 2026. arXiv:2503.18813
16. M. Costa et al. *Securing AI Agents with Information-Flow Control.* 2025. arXiv:2505.23643
17. L. Beurer-Kellner et al. *Design Patterns for Securing LLM Agents against Prompt Injections.* 2025. arXiv:2506.08837
18. Q. Zhan et al. *Adaptive Attacks Break Defenses Against Indirect Prompt Injection Attacks on LLM Agents.* Findings of NAACL 2025. arXiv:2503.00061
19. Y. Deng et al. *Multilingual Jailbreak Challenges in Large Language Models.* ICLR 2024. arXiv:2310.06474
20. Z.-X. Yong, C. Menghini, S. H. Bach. *Low-Resource Languages Jailbreak GPT-4.* NeurIPS 2023 SoLaR Workshop. arXiv:2310.02446

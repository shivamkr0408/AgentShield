# Research paper

`main.tex` is a self-contained IEEE conference paper (uses `IEEEtran`, bundled on Overleaf). It
has no local LaTeX dependency beyond a standard TeX distribution.

## Compile

- **Overleaf (easiest):** New Project → Upload → `main.tex` → set compiler to pdfLaTeX → Recompile.
- **Local:** `pdflatex main && pdflatex main` (run twice for references). Requires TeX Live/MiKTeX.

References are inline (`thebibliography`); no separate `.bib` run is needed. Replace the author
block and `[NAME]`/`[INSTITUTION]`/`[EMAIL]` placeholders. The numbers are the real results from
`eval/benchmark.py`; update the table if you retrain Layer 2 or add the multilingual set.

## Suggested venues (confirm current dates yourself)

1. **IEEE SaTML** (Conference on Secure and Trustworthy ML) — a strong fit; recent prompt-injection
   defenses (CaMeL, task-drift) appeared here. Submissions have typically been in the autumn.
2. **ACM AISec** (Workshop on AI and Security, co-located with CCS) — the venue where indirect
   prompt injection was first published; workshop-length, good for a focused contribution.
   Deadlines usually in the summer.
3. **ACL/EMNLP workshops** (e.g., TrustNLP, WOAH) or **ARR** — best for the *multilingual dataset*
   angle; rolling or per-conference deadlines.

These venues and dates change every cycle — **check the current call for papers before submitting.**
A longer version could target a security conference (USENIX Security, IEEE S\&P) once Layer 2 and the
full multilingual results are in.

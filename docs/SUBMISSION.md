# Submission handoff

Everything needed for submission, in one place.

## Links

| What | Link |
|---|---|
| Source code | https://github.com/shivamkr0408/AgentShield |
| Release v1.0.0 | https://github.com/shivamkr0408/AgentShield/releases/tag/v1.0.0 |
| Release v1.1.0 | https://github.com/shivamkr0408/AgentShield/releases/tag/v1.1.0 |
| Live dashboard | `[SET AFTER VERCEL DEPLOY]` e.g. https://agentshield.vercel.app |
| Live API | `[SET AFTER RENDER DEPLOY]` e.g. https://agentshield-api.onrender.com |
| API docs | `[RENDER URL]`/docs |
| AI demo (HF Space) | `[SET AFTER HF DEPLOY]` e.g. https://huggingface.co/spaces/shivamkr0408/AgentShield |
| Dataset | `[SET AFTER HF UPLOAD]` e.g. https://huggingface.co/datasets/shivamkr0408/agentshield-multilingual-injection |
| Project site (Pages) | `[AFTER ENABLING]` https://shivamkr0408.github.io/AgentShield |
| Demo video | `[YOUR YOUTUBE LINK]` |

## Submission files (in the repo)

- **Report:** `docs/report/report.md` (+ `report.docx`), figures in `docs/report/figures/`.
- **Paper:** `docs/paper/main.tex` (compile on Overleaf).
- **Slides:** `docs/viva/AgentShield.pptx`.
- **Viva Q&A:** `docs/viva/QUESTIONS.md`.
- **Video script:** `docs/demo/VIDEO_SCRIPT.md`.
- **Dataset docs:** `docs/dataset-card.md`, `docs/DATASHEET.md`, `docs/ETHICS.md`,
  `docs/hf-dataset-README.md`.
- **Literature summary:** `docs/literature-summary.md`.
- **Roadmap / progress:** `docs/ROADMAP.md`, `docs/PROGRESS.md`.

## What you still must do yourself

1. **Deploy** (accounts needed): Render (API, from `render.yaml`), Vercel (dashboard, root `web/`,
   set `VITE_API_URL`; then set `ALLOWED_ORIGINS` on Render to the Vercel URL), Hugging Face Space
   (from `spaces/huggingface/`), and the HF dataset (upload the split files + `hf-dataset-README.md`
   as `README.md`). Step-by-step instructions are in the chat.
2. **Enable GitHub Pages:** Settings → Pages → `main` / `docs`. Then fill the placeholder links in
   `docs/index.html`.
3. **Record the demo video** using `docs/demo/VIDEO_SCRIPT.md`; upload unlisted to YouTube; paste the
   link above and in the README.
4. **Fill name placeholders:** `[NAME]`, `[GUIDE]`, `[DEPARTMENT]`, etc. in `docs/report/report.md`,
   `docs/report/report.docx`, `docs/paper/main.tex`, and the slides.
5. **Paper submission:** confirm the venue and current deadline (`docs/paper/README.md`), finalize
   authors, submit.
6. **College submission:** print/submit the report and slides per your department's format.
7. **Strengthen results (optional but recommended):** train Layer 2 on GPU and add the human
   multilingual attack set, then re-run `eval/benchmark.py` and `eval/make_figures.py` to refresh the
   numbers everywhere.

## Verification checklist

- [ ] Every live link opens on mobile data (not just your Wi-Fi).
- [ ] No secrets in the repo or its history (only `…FAKE…` sandbox placeholders).
- [ ] README states which results are from the full local system vs. the live demo.
- [ ] Repo is public (required for the HF Space to clone) or shared with examiners.
- [ ] CI is green on `main`.

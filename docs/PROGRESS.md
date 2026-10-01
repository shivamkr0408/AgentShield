# Deployment & documentation progress

One line per step: status, links, and anything left for you.

| Step | Status | Notes / what's left for you |
|---|---|---|
| 1. Verify project works | ✅ done | 105 tests pass (clean-venv CI parity). Phases 1–9 all present. |
| 2. Docker verification | ✅ done | Built API (381 MB) + dashboard (94 MB); verified `/health`, `/config`, `/docs`, dashboard, `/scan`, `/stats`, and the **WebSocket live through nginx**. Model pull (`ollama pull`) is your large download. |
| 3. Prepare for hosting | ✅ done | `VITE_API_URL`+`wss://`, `ALLOWED_ORIGINS`+`$PORT`+`DEMO_MODE`, **Demo-mode badge** via `/config`, `render.yaml`, `web/vercel.json`, `spaces/huggingface/`, `WEB_PORT`. |
| 4. Deploy API (Render) | ⛔ you | Needs your Render account. Instructions in chat. |
| 5. Deploy dashboard (Vercel) | ⛔ you | Needs your Vercel account. Instructions in chat. |
| 6. GitHub Pages site | ✅ built / ⛔ enable | `docs/index.html` with architecture diagram + link buttons. Enable: Settings → Pages → `main` / `docs`, then fill the placeholder links. |
| 7. Hugging Face Space | ⛔ you | `spaces/huggingface/` ready (Docker, port 7860). Create + push the Space. |
| 8. Dataset release | ✅ docs / ⛔ upload | Card (`docs/hf-dataset-README.md`), `docs/DATASHEET.md`, `docs/ETHICS.md` done. Upload the split files + card to the HF dataset repo. Attack class currently = public English ingest; add the human multilingual set for the full story. |
| 9. README & release | ✅ done | Badges, links table, hosting, citation. **Release v1.1.0 created.** |
| 10. Project report | ✅ done | `docs/report/report.md` + `report.docx` (figures embedded), real numbers, cover/certificate placeholders. |
| 11. Research paper | ✅ done | `docs/paper/main.tex` (IEEE, compiles on Overleaf); 3 venue suggestions. |
| 12. Demo video script | ✅ done | `docs/demo/VIDEO_SCRIPT.md`; scripted demo via `DEMO_MODE`. Recording is yours. |
| 13. Viva deck + Q&A | ✅ done | `docs/viva/AgentShield.pptx` (12 slides) + `docs/viva/QUESTIONS.md` (25 Q&A). |
| 14. Final check & handoff | 🔄 after deploys | `docs/SUBMISSION.md` written; live-link verification pending your deploys. |

## Results status

Real numbers are in the report, from `eval/benchmark.py` on a public English injection test set
(deepset, 87 samples) with **Layer 1 + Layer 2 (xlm-roberta, 2 epochs) + learned fusion**:
**precision 0.88, recall 0.94, F1 0.91, FPR 0.071, attack-success 6.5%** (vs. keyword 0.19 recall /
81% ASR, and 100% undefended). Ablation: removing the classifier drops recall to 0 (it carries
recall); removing rules → 0.90. Latency p50 70 ms / p95 159 ms (classifier on CPU; rules alone
~0.1 ms). Figures regenerated. The multilingual numbers still need the human attack set (the public
ingest is English); Layer 3 needs Ollama.

## Repo / CI

- `main` pushed through all deployment + documentation commits. CI green.
- Releases: `v1.0.0` (full system), `v1.1.0` (deployment + documentation).
- No real secrets; only `…FAKE…` sandbox placeholders.

# Deployment & documentation progress

One line per step: status, links, and anything left for you.

| Step | Status | Notes / what's left for you |
|---|---|---|
| 1. Verify project works | ✅ done | 104 tests pass. Phases 1–9 all present (agent+tools, dataset, preprocessing, 3 detectors, canary, taint, firewall+fusion, API+WS, dashboard, adaptive attacker, eval). **Caveat:** the committed dataset is 41 benign records, 0 attacks, so headline attack-success/detection numbers are **[RESULT PENDING]** — see "Results blocker" below. |
| 2. Docker verification | ⏳ blocked (you) | Docker **client** present but the **daemon isn't running**. Start Docker Desktop, then run `DEMO_MODE=true docker compose up --build`; I can then verify endpoints. Full model pull (`ollama pull qwen2.5:7b`) is your step. |
| 3. Prepare for hosting | ✅ done | `VITE_API_URL`+`wss://` (web), `ALLOWED_ORIGINS`+`$PORT`+`DEMO_MODE` (api), **Demo-mode badge** on the dashboard via `GET /config`, `render.yaml`, `web/vercel.json`, `spaces/huggingface/`, compose env configurable. |
| 4. Deploy API (Render) | ⛔ you | Needs your Render account — instructions provided in chat. |
| 5. Deploy dashboard (Vercel) | ⛔ you | Needs your Vercel account — instructions provided in chat. |
| 6. GitHub Pages site | 🔄 partial | `docs/index.html` landing page exists; enabling Pages is your click. Will refine with a diagram once results exist. |
| 7. Hugging Face Space | ⛔ you | `spaces/huggingface/` ready; creating/pushing the Space is your step. |
| 8. Dataset release | 🔄 partial | Card/datasheet/ethics can be written now; the attack class is pending ingestion/annotation. |
| 9. README & release | 🔄 in progress | README has badges + hosting; results tables are [RESULT PENDING]. v1.1.0 release is your push/tag. |
| 10–13. Report / paper / video / viva | 🔄 pending decision | Depend on real results. See blocker. |
| 14. Final check & handoff | ⛔ pending | After deploys. |

## Results blocker (decision needed)

The evaluation **runs**, but there are **no attack samples** committed, so attack-success rate,
detection, per-language, and adaptive-attack numbers are `[RESULT PENDING]`. To get real numbers,
one of:
- **Ingest public injection datasets**: `pip install datasets` then `python -m dataset.ingest --all`
  (needs network; `datasets` was not installed in this environment on first try).
- **Add the human multilingual attack set** via `data/multilingual/` (the project's unique contribution).

Until then, the report/paper/deck will carry `[RESULT PENDING]` in results sections, as required
by the ground rules.

## Push / CI

- `main` is pushed through the hosting + demo-badge commits.
- CI (`.github/workflows/ci.yml`) runs on every push; a Windows-specific sandbox test was fixed
  to pass on the Linux runner.

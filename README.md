# AgentShield

**Provenance-Aware Defense Against Multilingual Prompt Injection in LLM Agents**

[![CI](https://github.com/shivamkr0408/AgentShield/actions/workflows/ci.yml/badge.svg)](https://github.com/shivamkr0408/AgentShield/actions/workflows/ci.yml)

AgentShield is a research prototype for evaluating layered defenses against indirect and multilingual prompt injection. The planned system combines provenance-aware preprocessing, detectors, canary tokens, taint tracking, a policy firewall, an adaptive attacker, and a live evaluation dashboard.

See [docs/ROADMAP.md](docs/ROADMAP.md) for the full 15-week plan and [docs/literature-summary.md](docs/literature-summary.md) for the Phase 0 literature summary.

## Links

| | |
|---|---|
| Source | https://github.com/shivamkr0408/AgentShield |
| Report | [docs/report/report.md](docs/report/report.md) ([.docx](docs/report/report.docx)) |
| Paper | [docs/paper/main.tex](docs/paper/main.tex) |
| Dataset card | [docs/dataset-card.md](docs/dataset-card.md) · [datasheet](docs/DATASHEET.md) · [ethics](docs/ETHICS.md) |
| Live Dashboard | https://agent-shield-six.vercel.app |
| API | https://agentshield-api-83kj.onrender.com |
| GitHub Pages | https://shivamkr0408.github.io/AgentShield/ |
| Hugging Face Demo | https://huggingface.co/spaces/shivamkrgupta/AgentShield |
| Hugging Face Dataset | https://huggingface.co/datasets/shivamkrgupta/AgentShield-dataset |

## Status

- Python 3.11+ package (`agents`, `api`, `eval`, `shield`) with development dependencies
- Phase 1: LangGraph test agent, mock tools behind a single hook point, 25 benign tasks, and an injection scenario runner
- Phase 2: dataset pipeline (schema, taxonomy, public-data adapters, multilingual annotation harness, benign hard negatives, stratified splits, dataset card)
- Phase 3: preprocessing (visible/hidden HTML split, decode + NFKC + invisible-strip + homoglyph map, optional OCR, chunk metadata)
- Phase 4: three detector layers (rule filter, xlm-roberta classifier, LLM-judge intent check) behind one interface, with a metrics harness
- Phase 5: canary tokens (leak tripwires with trace-back) and origin taint tracking (USER/PRIVATE/EXTERNAL) with a PRIVATE→EXTERNAL policy
- Phase 6: logistic risk fusion and a YAML action firewall (allow / sanitize / block, human approval with a fail-safe timeout)
- Phase 7: FastAPI backend (scan, check_action, incidents, approvals, live policy, stats), a WebSocket decision stream, SQLite persistence, and an `AgentShield.wrap()` SDK
- Phase 8: a live, responsive React dashboard (Overview, Incidents, Approvals, Playground, Policies, Results) that streams updates over the WebSocket
- Phase 9: an adaptive-attacker harness, baselines (keyword filter, OSS classifier), and an evaluation suite (metrics, ablation) that publishes to the dashboard
- Phase 10: Docker Compose (API + dashboard + Ollama), a paper-style report, and a viva demo script
- FastAPI health endpoint for the future evaluation service
- React/Vite dashboard shell, reachable from other devices on the LAN
- Module layout for every planned defense layer
- Literature summary and roadmap
- Initial smoke test

## Repository layout

```text
agentshield/
├── agents/        # Sandboxed test agents and mock tools
├── data/          # Attack and benign datasets
├── shield/        # Detection and defense layers
├── api/           # FastAPI and future WebSocket server
├── web/           # React dashboard
├── eval/          # Benchmark and ablation scripts
├── docs/          # Literature review and design notes
└── tests/         # Automated tests
```

## Local setup

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Install [Ollama](https://ollama.com/download) separately, then pull a local model and confirm it is reachable:

```powershell
ollama pull qwen2.5:7b
Invoke-RestMethod http://localhost:11434/api/tags
```

## Run the test agent

The agent needs Ollama running with the model named in `.env`.

```powershell
python -m agents "What is the top complaint in the customer feedback roundup?"
python -m agents.website                 # browse the mock intranet at http://127.0.0.1:5050
python -m eval.run benign                # usefulness on the 25 normal tasks
python -m eval.run injections --scenarios data/attacks/before_demo.json --verbose
```

Each evaluation writes `runs/<timestamp>-<suite>-<model>/report.json`, plus one JSONL trace per case. Injection scenario files are described in [data/attacks/README.md](data/attacks/README.md).

## Build the dataset

```powershell
python -m dataset.ingest --list        # public sources (ingest needs: pip install datasets)
python -m dataset.validate             # check the committed data
python -m dataset.build --heldout-category encoded_text   # write splits to data/generated/
```

See the [dataset card](docs/dataset-card.md) and the multilingual [annotation guidelines](data/multilingual/GUIDELINES.md).

## Run the detectors

```powershell
python -m eval.detect_eval --layer rules --split test   # Layer 1 (no extra deps)
pip install "agentshield[ml]"                            # Layer 2 classifier (GPU recommended)
python -m shield.detectors.train_classifier --epochs 3   # fine-tune xlm-roberta-base on Colab/Kaggle
python -m eval.detect_eval --layer intent                # Layer 3 needs Ollama running
```

Every layer implements `score(chunk, context) -> Signal`, and a `Signal` unpacks to `(score, reason)`. Metrics are written to `runs/detectors/`.

## Run the full defense end to end

```powershell
python -m dataset.build           # produce splits (needed before fitting fusion)
python -m eval.fit_fusion         # learn risk-fusion weights -> models/fusion.json
python -m eval.run benign --defense full --approver approve     # utility with the firewall
python -m eval.run injections --scenarios data/attacks/before_demo.json --defense full
```

The firewall ([shield/firewall/](shield/firewall/)) seeds canary tokens, tracks taint, scores incoming content with the detectors, fuses the signals ([shield/scoring.py](shield/scoring.py)), and applies the policy in [config/firewall.yaml](config/firewall.yaml). Sensitive or taint-flagged actions go to a human approver; unanswered requests are denied after a timeout.

## Run the API and dashboard

```powershell
python -m uvicorn api.main:app --reload --host 0.0.0.0
```

Interactive API docs are at `/docs`. The API exposes `/scan`, `/check_action`, `/events`,
`/incidents`, `/approvals`, `/policy`, `/stats`, and the `/ws/events` stream, backed by SQLite.

The dashboard lives in [web/](web/). For development with live reload:

```powershell
cd web; npm install; npm run dev     # Vite dev server, proxies the API to :8000
```

For a single-process demo, build the dashboard and let FastAPI serve it at `/`:

```powershell
cd web; npm run build
python -m uvicorn api.main:app --host 0.0.0.0    # open http://<your-ip>:8000 on any device
```

Embed the shield in your own agent with the SDK:

```python
from api.sdk import AgentShield
from agents.agent import run_agent

protected = AgentShield.wrap(run_agent)
protected("Summarize the reviews.", sandbox, model)
```

## Evaluate

```powershell
python -m dataset.build                                   # build the splits
python -m eval.fit_fusion                                 # learn fusion weights
python -m eval.benchmark --split test --publish http://localhost:8000   # metrics + ablation -> dashboard
python -m eval.run injections --scenarios data/attacks/before_demo.json --defense full
```

The adaptive attacker and baselines live in [eval/attacker/](eval/attacker/) and
[shield/detectors/baselines.py](shield/detectors/baselines.py). See the
[report](docs/report.md) and the [demo script](docs/demo-script.md).

## Deploy with Docker

Verified: `docker compose build` produces the API (~381 MB) and dashboard (~94 MB) images; the
dashboard is served through nginx, which proxies the API and the WebSocket.

Full stack (API + dashboard + Ollama) with a local model:

```powershell
docker compose up --build
docker compose exec ollama ollama pull qwen2.5:7b    # once; large download
```
Open the dashboard at `http://localhost:8080` and the API docs at `http://localhost:8000/docs`.

API + dashboard only (no model, demo mode) — handy for a quick check or hosting:

```powershell
# WEB_PORT lets you avoid a busy 8080; DEMO_MODE seeds one real illustrative incident.
$env:DEMO_MODE="true"; $env:WEB_PORT="8090"; docker compose up -d --no-deps --build api web
```
Then `http://localhost:8090` (dashboard) and `http://localhost:8000/docs` (API). The demo badge
appears top-right. Stop with `docker compose down`.

## Run checks## Run checks## Run checks

```powershell
python -m pytest
```

## Frontend

From `web/`, run `npm install` and `npm run dev`. The dev server listens on all interfaces, so a phone on the same network can open it using the URL that Vite prints. Requests to `/api/*` are proxied to the API on port 8000.

## Citation

```bibtex
@software{agentshield2026,
  title        = {AgentShield: Provenance-Aware Defense Against Multilingual Prompt Injection in LLM Agents},
  author       = {[NAME]},
  year         = {2026},
  url          = {https://github.com/shivamkr0408/AgentShield},
  note         = {Final-year project}
}
```

## License

MIT — see [LICENSE](LICENSE).

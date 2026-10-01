---
title: AgentShield
emoji: 🛡️
colorFrom: indigo
colorTo: green
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# AgentShield — live demo Space

Runs the AgentShield API and dashboard together on Hugging Face Spaces (free CPU) in
`DEMO_MODE`. The playground, canary/taint checks, incident replay, and the live decision
stream all work without a model. The LLM intent-check layer (Layer 3) and full agent runs
need Ollama and are **not** enabled here — see the local setup in the main repo for those,
and the report for the full-system results.

## How it works

This Space is self-contained: its `Dockerfile` clones the public GitHub repo
(`shivamkr0408/AgentShield`), builds the dashboard, and serves everything on port 7860. To
update the demo, restart the Space (it re-clones) or push the repo.

**The repo must be public** for the Space to clone it without a token.

Source: https://github.com/shivamkr0408/AgentShield

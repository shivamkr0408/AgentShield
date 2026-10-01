# Hugging Face Space (Docker SDK). Self-contained: clones the public repo, builds the
# dashboard, and serves the API + dashboard in demo mode on port 7860.
FROM node:22-slim AS web
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
WORKDIR /src
RUN git clone --depth 1 https://github.com/shivamkr0408/AgentShield.git .
RUN cd web && npm install && npm run build

FROM python:3.11-slim
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN git clone --depth 1 https://github.com/shivamkr0408/AgentShield.git .
COPY --from=web /src/web/dist ./web/dist
RUN pip install --no-cache-dir -e .

ENV DEMO_MODE=true \
    ALLOWED_ORIGINS=* \
    AGENTSHIELD_DB_URL=sqlite:////tmp/agentshield.db

EXPOSE 7860
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port 7860"]

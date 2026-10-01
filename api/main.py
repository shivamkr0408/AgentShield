"""AgentShield backend API.

A live service the dashboard and other agents use: score content, check proposed actions,
review history and incidents, resolve approvals, change policy, and stream every decision over
a WebSocket. Interactive docs are at /docs.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.db import make_sessionmaker
from api.events import EventBus
from api.schemas import ActionRequest, IncidentRequest, PolicyUpdate, ScanRequest
from api.service import ShieldService

WEB_DIST = Path(__file__).resolve().parent.parent / "web" / "dist"


def create_app(db_url: str | None = None, judge=None, demo: bool | None = None) -> FastAPI:
    app = FastAPI(
        title="AgentShield API",
        version="0.2.0",
        description="Provenance-aware defense against multilingual prompt injection: live scanning, "
        "action checks, incidents, approvals, policy, and a decision stream.",
    )
    # Restrict to the dashboard's origin(s) in production via ALLOWED_ORIGINS (comma-separated).
    raw_origins = os.getenv("ALLOWED_ORIGINS", "*")
    origins = ["*"] if raw_origins.strip() == "*" else [o.strip() for o in raw_origins.split(",") if o.strip()]
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])

    url = db_url or os.getenv("AGENTSHIELD_DB_URL", "sqlite:///agentshield.db")
    service = ShieldService(make_sessionmaker(url), judge=judge)
    bus = EventBus()
    app.state.service = service
    app.state.bus = bus

    if demo is None:
        demo = os.getenv("DEMO_MODE", "").strip().lower() in {"1", "true", "yes", "on"}
    service.demo = bool(demo)
    if demo:
        service.seed_demo()

    async def broadcast(event: dict) -> None:
        await bus.publish(event)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "agentshield", "phase": "api"}

    @app.get("/config")
    def config() -> dict:
        # The dashboard reads this to show a "Demo mode" badge on hosted/demo instances.
        return {"demo": bool(getattr(service, "demo", False)), "version": app.version}

    @app.post("/scan")
    async def scan(request: ScanRequest) -> dict:
        verdict, event = service.scan(request.content, request.source, request.incident_id)
        await broadcast(event)
        return verdict

    @app.post("/check_action")
    async def check_action(request: ActionRequest) -> dict:
        result, event = service.check_action(request.tool, request.args, request.incident_id)
        await broadcast(event)
        return result

    @app.post("/incidents")
    def create_incident(request: IncidentRequest) -> dict:
        return service.create_incident(request.task, request.secrets)

    @app.get("/events")
    def events(limit: int = 100, incident_id: str | None = None) -> list[dict]:
        return service.list_events(limit=limit, incident_id=incident_id)

    @app.get("/incidents")
    def list_incidents(limit: int = 50) -> list[dict]:
        return service.list_incidents(limit=limit)

    @app.get("/incidents/{incident_id}")
    def incident(incident_id: str) -> dict:
        found = service.get_incident(incident_id)
        if found is None:
            raise HTTPException(404, f"No incident {incident_id}")
        return found

    @app.get("/approvals")
    def approvals(status: str | None = "pending") -> list[dict]:
        return service.list_approvals(status=status)

    @app.get("/approvals/{approval_id}")
    def approval(approval_id: str) -> dict:
        found = service.get_approval(approval_id)
        if found is None:
            raise HTTPException(404, f"No approval {approval_id}")
        return found

    @app.post("/approvals/{approval_id}/approve")
    async def approve(approval_id: str) -> dict:
        return await _resolve(approval_id, True)

    @app.post("/approvals/{approval_id}/deny")
    async def deny(approval_id: str) -> dict:
        return await _resolve(approval_id, False)

    async def _resolve(approval_id: str, approve_it: bool) -> dict:
        resolved, event = service.resolve_approval(approval_id, approve_it)
        if resolved is None:
            raise HTTPException(404, f"No approval {approval_id}")
        if event:
            await broadcast(event)
        return resolved

    @app.get("/policy")
    def get_policy() -> dict:
        return service.get_policy()

    @app.put("/policy")
    def put_policy(update: PolicyUpdate) -> dict:
        return service.update_policy(update.thresholds, update.layers, update.approval_timeout_seconds)

    @app.get("/stats")
    def stats() -> dict:
        return service.stats()

    @app.get("/results")
    def get_results() -> dict:
        return service.get_results()

    @app.put("/results")
    def put_results(payload: dict) -> dict:
        return service.set_results(payload)

    @app.websocket("/ws/events")
    async def ws_events(websocket: WebSocket) -> None:
        await websocket.accept()
        queue = bus.subscribe()
        try:
            await websocket.send_json({"type": "hello", "subscribers": bus.subscriber_count})
            while True:
                event = await queue.get()
                await websocket.send_json(event)
        except WebSocketDisconnect:
            pass
        finally:
            bus.unsubscribe(queue)

    # Serve the built dashboard (one process for API + UI) when it exists.
    if WEB_DIST.is_dir():
        app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")

        @app.get("/")
        def index() -> FileResponse:
            return FileResponse(WEB_DIST / "index.html")

    return app


app = create_app()

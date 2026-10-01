"""Pydantic request bodies for the API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ScanRequest(BaseModel):
    content: str
    source: str = "playground"
    incident_id: str | None = None


class ActionRequest(BaseModel):
    tool: str
    args: dict[str, Any] = Field(default_factory=dict)
    incident_id: str | None = None


class IncidentRequest(BaseModel):
    task: str = ""
    secrets: list[str] = Field(default_factory=list)


class PolicyUpdate(BaseModel):
    thresholds: dict[str, float] | None = None
    layers: dict[str, bool] | None = None
    approval_timeout_seconds: float | None = None

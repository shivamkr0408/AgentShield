"""SQLAlchemy engine, session factory, and the ORM models for the backend store.

Events, incidents, approvals, and the live policy are persisted to SQLite so history and
replay survive a restart. Tests use an in-memory database.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class Base(DeclarativeBase):
    pass


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    task: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)

    def as_dict(self) -> dict[str, Any]:
        return {"id": self.id, "task": self.task, "created_at": self.created_at.isoformat()}


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    incident_id: Mapped[str | None] = mapped_column(ForeignKey("incidents.id"), nullable=True)
    type: Mapped[str] = mapped_column(String(32))        # "scan", "action", "approval"
    outcome: Mapped[str] = mapped_column(String(32), default="")
    tool: Mapped[str] = mapped_column(String(64), default="")
    source: Mapped[str] = mapped_column(String(256), default="")
    risk: Mapped[float] = mapped_column(default=0.0)
    layer: Mapped[str] = mapped_column(String(32), default="")  # which layer stopped it
    reason: Mapped[str] = mapped_column(String, default="")
    detail: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "incident_id": self.incident_id,
            "type": self.type,
            "outcome": self.outcome,
            "tool": self.tool,
            "source": self.source,
            "risk": self.risk,
            "layer": self.layer,
            "reason": self.reason,
            "detail": self.detail or {},
            "created_at": self.created_at.isoformat(),
        }


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    incident_id: Mapped[str | None] = mapped_column(ForeignKey("incidents.id"), nullable=True)
    tool: Mapped[str] = mapped_column(String(64))
    args: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    reason: Mapped[str] = mapped_column(String, default="")
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending/approved/denied
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
    resolved_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "incident_id": self.incident_id,
            "tool": self.tool,
            "args": self.args or {},
            "reason": self.reason,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }


class PolicyRow(Base):
    __tablename__ = "policy"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    thresholds: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    layers: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    approval_timeout_seconds: Mapped[float] = mapped_column(default=30.0)

    def as_dict(self) -> dict[str, Any]:
        return {
            "thresholds": self.thresholds or {},
            "layers": self.layers or {},
            "approval_timeout_seconds": self.approval_timeout_seconds,
        }


class ResultsRow(Base):
    __tablename__ = "results"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)


def make_sessionmaker(url: str = "sqlite:///agentshield.db") -> sessionmaker[Session]:
    kwargs: dict[str, Any] = {}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if ":memory:" in url or url in {"sqlite://", "sqlite:///:memory:"}:
            # A single shared connection, so every session sees the same in-memory database.
            kwargs["poolclass"] = StaticPool
    engine = create_engine(url, **kwargs)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)

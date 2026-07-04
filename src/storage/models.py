"""SQLAlchemy ORM models for local SQLite storage."""

from __future__ import annotations

import uuid
from datetime import datetime, date
from typing import Optional

from sqlalchemy import (
    Boolean, Date, DateTime, Float, ForeignKey,
    Integer, String, Text, Enum as SAEnum, UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    auth_method: Mapped[str] = mapped_column(String(20), default="api_key")
    language: Mapped[str] = mapped_column(String(10), default="en")
    voice_gender: Mapped[str] = mapped_column(String(10), default="female")
    theme: Mapped[str] = mapped_column(String(10), default="system")
    hotword_phrase: Mapped[str] = mapped_column(String(100), default="hey jarvis")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ProviderConfig(Base):
    __tablename__ = "provider_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    auth_method: Mapped[str] = mapped_column(String(20), default="api_key")
    credential_key: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ollama_base_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    fallback_priority: Mapped[int] = mapped_column(Integer, default=99)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TierOverride(Base):
    __tablename__ = "tier_overrides"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    pattern: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    tier: Mapped[str] = mapped_column(String(10), nullable=False)  # simple|medium|complex
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    provider_name: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="en")
    status: Mapped[str] = mapped_column(String(30), default="completed")
    total_tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)

    requests: Mapped[list["Request"]] = relationship("Request", back_populates="session")


class Request(Base):
    __tablename__ = "requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id"), nullable=False)
    cleaned_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    tier: Mapped[str] = mapped_column(String(10), nullable=False)
    tier_overridden: Mapped[bool] = mapped_column(Boolean, default=False)
    approval_status: Mapped[str] = mapped_column(String(20), default="not_required")
    final_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    provider_name: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    fallback_triggered: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    session: Mapped["Session"] = relationship("Session", back_populates="requests")


class UsageRecord(Base):
    __tablename__ = "usage_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    provider_name: Mapped[str] = mapped_column(String(20), nullable=False)
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    is_local: Mapped[bool] = mapped_column(Boolean, default=False)
    cloud_equivalent_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)


class RetryQueueItem(Base):
    __tablename__ = "retry_queue_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    cleaned_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    tier: Mapped[str] = mapped_column(String(10), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    last_attempted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")


class MemoryEntry(Base):
    __tablename__ = "memory_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    source_session_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SkillRecord(Base):
    __tablename__ = "skill_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    skill_id: Mapped[str] = mapped_column(String(100), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(20), nullable=False)
    installed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)


class McpConnection(Base):
    __tablename__ = "mcp_connections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    service_name: Mapped[str] = mapped_column(String(100), nullable=False)
    server_url: Mapped[str] = mapped_column(String(500), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(20), nullable=False)
    auth_method: Mapped[str] = mapped_column(String(20), default="none")
    credential_key: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    connected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AgentBackend(Base):
    """Registered agent backend (built-in router or external HTTP service)."""

    __tablename__ = "agent_backends"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    # built_in | openai_compatible | langgraph
    backend_type: Mapped[str] = mapped_column(String(30), nullable=False, default="built_in")
    base_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    model_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    is_built_in: Mapped[bool] = mapped_column(Boolean, default=False)
    # connected | degraded | disconnected | unknown
    health_status: Mapped[str] = mapped_column(String(20), default="unknown")
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    fallback_priority: Mapped[int] = mapped_column(Integer, default=99)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    dispatch_events: Mapped[list["BackendDispatchEvent"]] = relationship(
        "BackendDispatchEvent",
        back_populates="backend",
        foreign_keys="BackendDispatchEvent.backend_name",
        primaryjoin="AgentBackend.name == BackendDispatchEvent.backend_name",
    )


class BackendDispatchEvent(Base):
    """Audit log entry for each request dispatched to an agent backend."""

    __tablename__ = "backend_dispatch_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    backend_name: Mapped[str] = mapped_column(String(100), nullable=False)
    request_id: Mapped[str] = mapped_column(String(36), nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fallback_triggered: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    backend: Mapped[Optional["AgentBackend"]] = relationship(
        "AgentBackend",
        back_populates="dispatch_events",
        foreign_keys=[backend_name],
        primaryjoin="AgentBackend.name == BackendDispatchEvent.backend_name",
    )

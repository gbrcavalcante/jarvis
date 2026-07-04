"""Async CRUD helpers for AgentBackend and BackendDispatchEvent."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.storage.models import AgentBackend, BackendDispatchEvent


async def list_backends(db: AsyncSession) -> list[AgentBackend]:
    """Return all registered backends ordered by fallback_priority."""
    result = await db.execute(
        select(AgentBackend).order_by(AgentBackend.fallback_priority, AgentBackend.created_at)
    )
    return list(result.scalars().all())


async def get_backend(db: AsyncSession, backend_id: str) -> Optional[AgentBackend]:
    """Return a backend by ID, or None."""
    result = await db.execute(select(AgentBackend).where(AgentBackend.id == backend_id))
    return result.scalar_one_or_none()


async def get_backend_by_name(db: AsyncSession, name: str) -> Optional[AgentBackend]:
    """Return a backend by unique name, or None."""
    result = await db.execute(select(AgentBackend).where(AgentBackend.name == name))
    return result.scalar_one_or_none()


async def get_active_backend(db: AsyncSession) -> Optional[AgentBackend]:
    """Return the currently active backend, or None."""
    result = await db.execute(select(AgentBackend).where(AgentBackend.is_active == True))  # noqa: E712
    return result.scalar_one_or_none()


async def create_backend(
    db: AsyncSession,
    name: str,
    backend_type: str,
    base_url: Optional[str] = None,
    model_name: Optional[str] = None,
    fallback_priority: int = 99,
) -> AgentBackend:
    """Insert a new backend row."""
    backend = AgentBackend(
        name=name,
        backend_type=backend_type,
        base_url=base_url,
        model_name=model_name,
        fallback_priority=fallback_priority,
        is_active=False,
        is_built_in=False,
        health_status="unknown",
    )
    db.add(backend)
    await db.commit()
    await db.refresh(backend)
    return backend


async def update_backend(
    db: AsyncSession,
    backend_id: str,
    **kwargs: object,
) -> Optional[AgentBackend]:
    """Update mutable fields on an existing backend."""
    backend = await get_backend(db, backend_id)
    if backend is None:
        return None
    for key, value in kwargs.items():
        setattr(backend, key, value)
    await db.commit()
    await db.refresh(backend)
    return backend


async def set_active_backend(db: AsyncSession, backend_id: str) -> Optional[AgentBackend]:
    """Deactivate all backends, then activate the given one."""
    await db.execute(update(AgentBackend).values(is_active=False))
    backend = await get_backend(db, backend_id)
    if backend is None:
        return None
    backend.is_active = True
    await db.commit()
    await db.refresh(backend)
    return backend


async def delete_backend(db: AsyncSession, backend_id: str) -> bool:
    """Delete a backend by ID. Returns False if not found or is built-in."""
    backend = await get_backend(db, backend_id)
    if backend is None or backend.is_built_in:
        return False
    # If deleting the active backend, activate the built-in router
    if backend.is_active:
        built_in = await _get_built_in(db)
        if built_in:
            built_in.is_active = True
    await db.delete(backend)
    await db.commit()
    return True


async def write_dispatch_event(
    db: AsyncSession,
    backend_name: str,
    request_id: str,
    latency_ms: float,
    success: bool,
    error_message: Optional[str] = None,
    fallback_triggered: bool = False,
) -> BackendDispatchEvent:
    """Append an audit log entry for a backend dispatch."""
    event = BackendDispatchEvent(
        backend_name=backend_name,
        request_id=request_id,
        latency_ms=latency_ms,
        success=success,
        error_message=error_message,
        fallback_triggered=fallback_triggered,
    )
    db.add(event)
    await db.commit()
    return event


async def update_health_status(
    db: AsyncSession,
    backend_id: str,
    health_status: str,
    increment_error: bool = False,
) -> None:
    """Update health_status and optionally increment error_count."""
    backend = await get_backend(db, backend_id)
    if backend is None:
        return
    backend.health_status = health_status
    if increment_error:
        backend.error_count += 1
    else:
        backend.error_count = 0
        backend.last_seen_at = datetime.utcnow()
    await db.commit()


async def _get_built_in(db: AsyncSession) -> Optional[AgentBackend]:
    result = await db.execute(select(AgentBackend).where(AgentBackend.is_built_in == True))  # noqa: E712
    return result.scalar_one_or_none()


async def seed_built_in_router(db: AsyncSession) -> None:
    """Create the Built-in Router row if it does not yet exist."""
    existing = await get_backend_by_name(db, "Built-in Router")
    if existing is not None:
        return
    router = AgentBackend(
        name="Built-in Router",
        backend_type="built_in",
        is_active=True,
        is_built_in=True,
        health_status="connected",
        fallback_priority=0,
    )
    db.add(router)
    await db.commit()

"""ProviderConfig CRUD — SQLite storage. Credentials stay in OS keychain."""

from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.storage.models import ProviderConfig


async def list_providers(db: AsyncSession) -> list[ProviderConfig]:
    result = await db.execute(select(ProviderConfig).order_by(ProviderConfig.fallback_priority))
    return list(result.scalars().all())


async def get_provider(db: AsyncSession, name: str) -> ProviderConfig | None:
    result = await db.execute(select(ProviderConfig).where(ProviderConfig.name == name))
    return result.scalar_one_or_none()


async def upsert_provider(db: AsyncSession, name: str, **kwargs: object) -> ProviderConfig:
    provider = await get_provider(db, name)
    if provider is None:
        provider = ProviderConfig(name=name, **kwargs)
        db.add(provider)
    else:
        for key, value in kwargs.items():
            setattr(provider, key, value)
    await db.commit()
    await db.refresh(provider)
    return provider


async def set_active_provider(db: AsyncSession, name: str) -> None:
    """Deactivate all providers, then activate the named one."""
    await db.execute(update(ProviderConfig).values(is_active=False))
    await db.execute(
        update(ProviderConfig).where(ProviderConfig.name == name).values(is_active=True)
    )
    await db.commit()


async def delete_provider(db: AsyncSession, name: str) -> None:
    provider = await get_provider(db, name)
    if provider:
        await db.delete(provider)
        await db.commit()

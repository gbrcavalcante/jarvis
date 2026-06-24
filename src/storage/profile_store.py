"""UserProfile CRUD — local SQLite storage."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.storage.models import UserProfile


async def get_profile(session: AsyncSession) -> UserProfile | None:
    result = await session.execute(select(UserProfile).limit(1))
    return result.scalar_one_or_none()


async def upsert_profile(session: AsyncSession, **kwargs: object) -> UserProfile:
    profile = await get_profile(session)
    if profile is None:
        profile = UserProfile(**kwargs)
        session.add(profile)
    else:
        for key, value in kwargs.items():
            setattr(profile, key, value)
    await session.commit()
    await session.refresh(profile)
    return profile

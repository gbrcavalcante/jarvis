"""SQLite database engine and session factory (aiosqlite backend)."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.storage.models import Base


def _db_path() -> Path:
    import sys
    if sys.platform == "win32":
        base = Path.home() / "AppData" / "Roaming" / "JARVIS"
    else:
        base = Path.home() / ".local" / "share" / "jarvis"
    base.mkdir(parents=True, exist_ok=True)
    return base / "jarvis.db"


_engine = create_async_engine(
    f"sqlite+aiosqlite:///{_db_path()}",
    echo=False,
)

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=_engine,
    expire_on_commit=False,
)


async def init_db() -> None:
    """Create all tables if they don't exist. Called once at application startup."""
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:  # type: ignore[return]
    """FastAPI dependency that yields a database session."""
    async with AsyncSessionLocal() as session:
        yield session

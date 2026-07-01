# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Infrastructure — Doc 07 §Layers
# Dependency rule: infrastructure implements interfaces defined by domain — Doc 07 §Dependency Rules
# ORM: SQLAlchemy 2.0 async — Doc 03 §Core Stack
# Per Doc 00 §14.11
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from quant_hub.config import settings

engine: AsyncEngine = create_async_engine(
    settings.database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    echo=settings.debug,
)

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

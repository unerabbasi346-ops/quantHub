# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Test layer: integration tests exercise the real Postgres schema (Step 1.1
# migration c3a8f2b91e4d + Step 1.2 follow-up a428732d6bfe) through the
# async engine (Step 0.4, infrastructure/database.py) — Doc 09 §Migration
# Strategy: migrations, not test-only schema, are the source of truth.
# Per Doc 00 §14.11
#
# JUDGMENT CALL (Doc 00 §14.5/§14.7 — flagged, not silently decided): this
# is the project's first pytest suite — no tests/ directory or pytest
# config predates Step 1.3. The fixtures below are the minimum scaffolding
# needed to satisfy Step 1.3's explicit instruction to test the new
# repository methods against the running local Postgres container; general
# test-framework concerns (factories, CI wiring, coverage config) are out
# of scope and not attempted here.
#
# Requires DATABASE_URL (or a working .env) pointing at a live Postgres
# with both migrations applied — see docker/docker-compose.yml.
from __future__ import annotations

from collections.abc import AsyncIterator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession, create_async_engine

from quant_hub.config import settings


@pytest_asyncio.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    """Function-scoped: pytest-asyncio gives each test its own event loop,
    and asyncpg connections/pools are bound to the loop they were created
    on, so a session-scoped engine breaks on the second test ("another
    operation is in progress" / "Event loop is closed").
    """
    eng = create_async_engine(settings.database_url)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db_conn(engine: AsyncEngine) -> AsyncIterator[AsyncConnection]:
    """One connection + one outer transaction per test, rolled back after.

    Repository methods (persistence/repositories/market_data.py) deliberately
    never call commit() — transaction-boundary ownership belongs to the
    caller (Doc 07 §Implementation Rules) — so binding a session to a
    connection whose outer transaction is rolled back here gives each test
    full isolation without leaving data in the shared dev database.
    """
    async with engine.connect() as conn:
        trans = await conn.begin()
        yield conn
        await trans.rollback()


@pytest_asyncio.fixture
async def db_session(db_conn: AsyncConnection) -> AsyncIterator[AsyncSession]:
    session = AsyncSession(bind=db_conn, expire_on_commit=False)
    yield session
    await session.close()

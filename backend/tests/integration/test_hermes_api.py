# Governing specification: Doc 07 §API Standards. Integration test for the
# Hermes observability surface (mounted at /api/hermes — see
# hermes/api/hermes_router.py and main.py), following the same
# ASGITransport + rolled-back-transaction pattern test_api_endpoints.py
# established, plus test_ml_api.py's fresh-Redis-client override (the global
# redis_pool is bound to whichever event loop first used it; a per-test
# client sidesteps that).
from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from quant_hub.config import settings
from quant_hub.infrastructure.cache import get_redis
from quant_hub.infrastructure.database import get_session
from quant_hub.main import app


@pytest_asyncio.fixture
async def api() -> AsyncIterator[tuple[AsyncClient, AsyncSession]]:
    engine = create_async_engine(settings.database_url)
    conn = await engine.connect()
    trans = await conn.begin()
    session = AsyncSession(bind=conn, join_transaction_mode="create_savepoint")
    fresh_redis = Redis.from_url(settings.redis_url, decode_responses=True)

    async def _override_get_session() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_session] = _override_get_session
    app.dependency_overrides[get_redis] = lambda: fresh_redis
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client, session
    finally:
        app.dependency_overrides.clear()
        await session.close()
        await trans.rollback()
        await conn.close()
        await engine.dispose()
        await fresh_redis.aclose()


@pytest.mark.asyncio
async def test_hermes_status_shape_and_health_score(api) -> None:
    client, _session = api

    resp = await client.get("/api/hermes/status")

    assert resp.status_code == 200
    data = resp.json()["data"]

    assert 0.0 <= data["health_score"] <= 100.0
    service_names = {s["name"] for s in data["services"]}
    assert service_names == {"backend", "database", "redis"}
    backend = next(s for s in data["services"] if s["name"] == "backend")
    assert backend["status"] == "UP"

    for field in ("assets", "funding", "strategies", "models", "training_jobs", "generated_at"):
        assert field in data


@pytest.mark.asyncio
async def test_hermes_health_is_a_lighter_summary(api) -> None:
    client, _session = api

    resp = await client.get("/api/hermes/health")

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "health_score" in data
    assert "strategy_engine" in data and "active_count" in data["strategy_engine"]
    assert "data_pipeline" in data and {"fresh_count", "stale_count", "dead_count"} <= data["data_pipeline"].keys()
    assert "ml_engine" in data and "trained_count" in data["ml_engine"]
    assert "execution_engine" in data and "orders_today" in data["execution_engine"]


@pytest.mark.asyncio
async def test_hermes_pipeline_strategies_ml_endpoints_respond(api) -> None:
    client, _session = api

    pipeline = await client.get("/api/hermes/pipeline")
    strategies = await client.get("/api/hermes/strategies")
    ml = await client.get("/api/hermes/ml")

    assert pipeline.status_code == 200
    assert "assets" in pipeline.json()["data"]
    assert strategies.status_code == 200
    assert "strategies" in strategies.json()["data"]
    assert ml.status_code == 200
    assert {"models", "training_jobs"} <= ml.json()["data"].keys()

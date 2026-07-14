# Unit tests for hermes/monitors/service_health.py — DB/Redis mocked, no
# live connections. Per Doc 00 §14.11 test-layer conventions.
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from quant_hub.hermes.monitors.service_health import (
    STATUS_DOWN,
    STATUS_NOT_CONFIGURED,
    STATUS_UP,
    check_backend,
    check_database,
    check_redis,
)


def test_check_backend_is_always_up() -> None:
    result = check_backend()
    assert result.name == "backend"
    assert result.status == STATUS_UP
    assert result.latency_ms == 0.0


@pytest.mark.asyncio
async def test_check_database_up_on_successful_select() -> None:
    session = AsyncMock()
    session.execute = AsyncMock(return_value=None)

    result = await check_database(session)

    session.execute.assert_awaited_once()
    assert result.name == "database"
    assert result.status == STATUS_UP
    assert result.latency_ms is not None
    assert result.latency_ms >= 0.0


@pytest.mark.asyncio
async def test_check_database_down_when_execute_raises() -> None:
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=ConnectionError("no route to host"))

    result = await check_database(session)

    assert result.status == STATUS_DOWN
    assert result.latency_ms is None
    assert "no route to host" in result.detail


@pytest.mark.asyncio
async def test_check_redis_up_on_successful_ping() -> None:
    redis = AsyncMock()
    redis.ping = AsyncMock(return_value=True)

    result = await check_redis(redis, "redis://localhost:6379/0")

    redis.ping.assert_awaited_once()
    assert result.status == STATUS_UP
    assert result.latency_ms is not None


@pytest.mark.asyncio
async def test_check_redis_down_when_ping_raises() -> None:
    redis = AsyncMock()
    redis.ping = AsyncMock(side_effect=ConnectionError("connection refused"))

    result = await check_redis(redis, "redis://localhost:6379/0")

    assert result.status == STATUS_DOWN
    assert result.latency_ms is None


@pytest.mark.asyncio
async def test_check_redis_not_configured_when_url_empty() -> None:
    redis = AsyncMock()

    result = await check_redis(redis, "")

    redis.ping.assert_not_awaited()
    assert result.status == STATUS_NOT_CONFIGURED

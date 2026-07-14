# Hermes monitor: backend/database/Redis liveness — direct connectivity
# checks only (a SELECT 1, a PING), never anything that touches a financial
# table. See quant_hub/hermes/__init__.py for the import boundary this
# package is held to.
from __future__ import annotations

import time
from dataclasses import dataclass

from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

STATUS_UP = "UP"
STATUS_DOWN = "DOWN"
STATUS_NOT_CONFIGURED = "NOT_CONFIGURED"


@dataclass(frozen=True)
class ServiceStatus:
    name: str
    status: str  # UP | DOWN | NOT_CONFIGURED
    latency_ms: float | None
    detail: str


def check_backend() -> ServiceStatus:
    # Trivially UP — this code is executing inside the backend process
    # answering the request. Included for a complete, uniform service list
    # rather than a special-cased omission.
    return ServiceStatus(name="backend", status=STATUS_UP, latency_ms=0.0, detail="quant-hub-api")


async def check_database(session: AsyncSession) -> ServiceStatus:
    start = time.perf_counter()
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 — surfaced as a DOWN status, never swallowed
        return ServiceStatus(name="database", status=STATUS_DOWN, latency_ms=None, detail=str(exc))
    latency_ms = (time.perf_counter() - start) * 1000
    return ServiceStatus(name="database", status=STATUS_UP, latency_ms=latency_ms, detail="postgres")


async def check_redis(redis: Redis, redis_url: str) -> ServiceStatus:
    if not redis_url:
        return ServiceStatus(name="redis", status=STATUS_NOT_CONFIGURED, latency_ms=None, detail="REDIS_URL not set")
    start = time.perf_counter()
    try:
        await redis.ping()
    except Exception as exc:  # noqa: BLE001 — surfaced as a DOWN status, never swallowed
        return ServiceStatus(name="redis", status=STATUS_DOWN, latency_ms=None, detail=str(exc))
    latency_ms = (time.perf_counter() - start) * 1000
    return ServiceStatus(name="redis", status=STATUS_UP, latency_ms=latency_ms, detail="cache")

# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Infrastructure — Doc 07 §Layers
# Cache: Redis — Doc 03 §Core Stack
# Per Doc 00 §14.11
from __future__ import annotations

from redis.asyncio import ConnectionPool, Redis

from quant_hub.config import settings

redis_pool: ConnectionPool = ConnectionPool.from_url(
    settings.redis_url,
    decode_responses=True,
)


def get_redis() -> Redis:
    return Redis(connection_pool=redis_pool)

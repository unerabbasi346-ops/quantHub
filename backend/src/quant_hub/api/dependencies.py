# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Presentation/API — Doc 07 §Layers
# Dependency injection wiring — Doc 07 §Implementation Rules
# Per Doc 00 §14.11
from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from quant_hub.infrastructure.cache import get_redis
from quant_hub.infrastructure.database import get_session

# Annotated aliases consumed by route handlers via FastAPI Depends()
# Doc 07 §Implementation Rules: dependency injection for external resources
DbSession = Annotated[AsyncSession, Depends(get_session)]
CacheClient = Annotated[Redis, Depends(get_redis)]

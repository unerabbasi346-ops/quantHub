# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Persistence — Doc 07 §Layers
# Repository pattern: concrete SQLAlchemy implementation — Doc 07 §Implementation Rules
# Dependency rule: infrastructure implements domain interfaces — Doc 07 §Dependency Rules
# Per Doc 00 §14.11
from __future__ import annotations

from uuid import UUID

from quant_hub.domain.market_data.interfaces import (
    AssetRepository,
    OHLCVRepository,
    TickRepository,
)
from quant_hub.persistence.repositories.base import BaseRepository


class SQLAlchemyAssetRepository(BaseRepository[object], AssetRepository):
    """Concrete repository for market_data.assets — Doc 07 §Implementation Rules."""

    async def get_by_id(self, asset_id: UUID) -> object | None:
        return None  # stub: SQLAlchemy query in Step 0.5+

    async def get_by_symbol_exchange(self, symbol: str, exchange: str) -> object | None:
        return None  # stub

    async def list_active(self) -> list[object]:
        return []  # stub


class SQLAlchemyOHLCVRepository(BaseRepository[object], OHLCVRepository):
    """Concrete repository for market_data.ohlcv_bars."""

    async def get_bars(self, asset_id: UUID, interval: str, limit: int = 100) -> list[object]:
        return []  # stub


class SQLAlchemyTickRepository(BaseRepository[object], TickRepository):
    """Concrete repository for market_data.ticks."""

    async def get_latest(self, asset_id: UUID) -> object | None:
        return None  # stub

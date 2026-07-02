# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Persistence — Doc 07 §Layers
# Repository pattern: concrete SQLAlchemy implementation — Doc 07 §Implementation Rules
# Dependency rule: infrastructure implements domain interfaces — Doc 07 §Dependency Rules
# Per Doc 00 §14.11
#
# Step 1.2 addition: upsert/save stubs below back the new write methods on
# the domain interfaces (see domain/market_data/interfaces.py). They raise
# NotImplementedError rather than silently no-op'ing like the pre-existing
# read stubs — a write path that pretends to succeed without persisting
# would be a false negative for ingestion callers, which is worse than a
# loud failure. No SQLAlchemy ORM models exist yet for market_data.* (Step
# 1.1 shipped raw-SQL Alembic DDL only); real queries are Step 1.3+.
from __future__ import annotations

from uuid import UUID

from quant_hub.domain.market_data.entities import AssetRef, OHLCVBar, Tick
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

    async def upsert(self, asset: AssetRef) -> UUID:
        raise NotImplementedError(
            "market_data.assets has no SQLAlchemy ORM model yet — stub pending Step 1.3+"
        )  # stub: Step 1.2 skeleton


class SQLAlchemyOHLCVRepository(BaseRepository[object], OHLCVRepository):
    """Concrete repository for market_data.ohlcv_bars."""

    async def get_bars(self, asset_id: UUID, interval: str, limit: int = 100) -> list[object]:
        return []  # stub

    async def upsert_bars(self, bars: list[OHLCVBar]) -> int:
        raise NotImplementedError(
            "market_data.ohlcv_bars has no SQLAlchemy ORM model yet — stub pending Step 1.3+"
        )  # stub: Step 1.2 skeleton


class SQLAlchemyTickRepository(BaseRepository[object], TickRepository):
    """Concrete repository for market_data.ticks."""

    async def get_latest(self, asset_id: UUID) -> object | None:
        return None  # stub

    async def save_tick(self, tick: Tick) -> None:
        raise NotImplementedError(
            "market_data.ticks has no SQLAlchemy ORM model yet — stub pending Step 1.3+"
        )  # stub: Step 1.2 skeleton

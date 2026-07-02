# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Domain — Doc 07 §Layers
# Service: Market Data — Doc 07 §Core Services
# Dependency rule: domain defines interfaces; infrastructure implements them
#   — Doc 07 §Dependency Rules
# Domain logic never depends on frameworks — Doc 07 §Dependency Rules
# Per Doc 00 §14.11
#
# Step 1.2 addition: upsert/save methods below extend these contracts to
# support the ingestion "Persist" pipeline stage — Doc 11 §2 Historical Data
# Ingestion. The Step 0.4 interfaces only covered reads; writes are added
# additively (existing method signatures unchanged) rather than redefined,
# per Doc 00 §14.6 ("AI agents may implement... shall not redefine
# architecture" — this fills an omission in the persistence contract the
# ingestion pipeline requires, it does not change existing behavior).
from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from quant_hub.domain.market_data.entities import AssetRef, OHLCVBar, Tick


class AssetRepository(ABC):
    """Persistence contract for market_data.assets — Doc 07 §Implementation Rules."""

    @abstractmethod
    async def get_by_id(self, asset_id: UUID) -> object | None: ...

    @abstractmethod
    async def get_by_symbol_exchange(self, symbol: str, exchange: str) -> object | None: ...

    @abstractmethod
    async def list_active(self) -> list[object]: ...

    @abstractmethod
    async def upsert(self, asset: AssetRef) -> UUID:
        """Resolve-or-create the asset row, returning its id.

        Added in Step 1.2 for the ingestion "Persist" stage — Doc 11 §2.
        Idempotent on the assets_symbol_exchange_uq constraint (Doc 09,
        Step 1.1 migration) per Doc 11 §2 Requirements ("Idempotent
        ingestion").
        """
        ...


class OHLCVRepository(ABC):
    """Persistence contract for market_data.ohlcv_bars — Doc 07 §Implementation Rules."""

    @abstractmethod
    async def get_bars(
        self, asset_id: UUID, interval: str, limit: int = 100
    ) -> list[object]: ...

    @abstractmethod
    async def upsert_bars(self, bars: list[OHLCVBar]) -> int:
        """Idempotently persist bars, returning the count written.

        Added in Step 1.2 for the ingestion "Persist" stage — Doc 11 §2.
        Idempotent on the ohlcv_bars_asset_interval_ts_uq constraint
        (Doc 09, Step 1.1 migration) per Doc 11 §2 Requirements
        ("Idempotent ingestion").
        """
        ...


class TickRepository(ABC):
    """Persistence contract for market_data.ticks — Doc 07 §Implementation Rules."""

    @abstractmethod
    async def get_latest(self, asset_id: UUID) -> object | None: ...

    @abstractmethod
    async def save_tick(self, tick: Tick) -> None:
        """Append a tick row — Doc 11 §2 Persist stage.

        Added in Step 1.2. GAP (flagged, not silently resolved): ticks are
        described as append-only (Doc 11 §7 "append-only synchronization")
        but the Step 1.1 migration defines no unique constraint on
        market_data.ticks, so no DB-enforced idempotency key exists for
        individual ticks the way it does for assets/bars. Duplicate-tick
        prevention is therefore not guaranteed at this layer.
        """
        ...

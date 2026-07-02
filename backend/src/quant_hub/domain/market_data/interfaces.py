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
from datetime import datetime
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
        ("Idempotent ingestion"). This UNIQUE constraint is also the
        mechanism behind Doc 11 §7 "Prevent duplicate publication" for
        bars — a duplicate bar cannot be persisted twice, only revised.
        """
        ...

    @abstractmethod
    async def get_latest_ts(self, asset_id: UUID, interval: str) -> datetime | None:
        """Most recent persisted bar timestamp for (asset_id, interval), or None.

        Added in Step 1.9 for Doc 11 §7 "Detect late-arriving data" — the
        watermark a newly-acquired bar's ts is compared against. Narrower
        than get_bars() (returns a scalar, not full rows) since that's all
        late-arrival detection needs; get_bars() remains unimplemented
        pending a real consumer.
        """
        ...


class TickRepository(ABC):
    """Persistence contract for market_data.ticks — Doc 07 §Implementation Rules."""

    @abstractmethod
    async def get_latest(self, asset_id: UUID) -> object | None: ...

    @abstractmethod
    async def save_tick(self, tick: Tick) -> None:
        """Idempotently append a tick row — Doc 11 §2 Persist stage, §7 append-only.

        Added in Step 1.2; idempotency resolved in Step 1.2 follow-up
        migration a428732d6bfe, which added
        ticks_asset_ts_feed_origin_uq UNIQUE (asset_id, ts, feed_origin) to
        market_data.ticks (Doc 09, migration a428732d6bfe). Implementations
        (Step 1.3+) must use INSERT ... ON CONFLICT (asset_id, ts,
        feed_origin) DO NOTHING per that migration's "Consequence for
        callers" note, so legitimate retries are absorbed rather than
        raising IntegrityError. See that migration for the residual
        collision-risk limitation this key does not close. This same
        constraint is the mechanism behind Doc 11 §7 "Prevent duplicate
        publication" for ticks.
        """
        ...

    @abstractmethod
    async def get_latest_ts(self, asset_id: UUID) -> datetime | None:
        """Most recent persisted tick timestamp for asset_id, or None.

        Added in Step 1.9 for Doc 11 §7 "Detect late-arriving data" — see
        OHLCVRepository.get_latest_ts for the same rationale.
        """
        ...

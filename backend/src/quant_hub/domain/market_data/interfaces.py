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

from quant_hub.domain.market_data.entities import (
    Asset,
    AssetRef,
    CorporateAction,
    FundingRate,
    OHLCVBar,
    OpenInterest,
    Tick,
)


class AssetRepository(ABC):
    """Persistence contract for market_data.assets — Doc 07 §Implementation Rules."""

    @abstractmethod
    async def get_by_id(self, asset_id: UUID) -> Asset | None:
        """The persisted Asset for `asset_id`, or None if absent/soft-deleted.

        Return type tightened from `object` to `Asset` in Step 4.1 (API
        Foundation), its first real consumer (GET /v1/assets/{id}) — the
        previously-stubbed placeholder type is replaced now that a concrete
        read shape exists.
        """
        ...

    @abstractmethod
    async def get_by_symbol_exchange(self, symbol: str, exchange: str) -> UUID | None:
        """Resolve an existing asset's id by natural key, or None if unregistered.

        Implemented in Step 2.4 for MarketDataView's AssetRef -> asset_id
        resolution (infrastructure/strategy_engine/market_data_view.py) —
        the first real consumer of this previously-stubbed method.
        """
        ...

    @abstractmethod
    async def list_active(self) -> list[Asset]:
        """All active (is_active, not soft-deleted) assets, ordered stably.

        Return type tightened from `list[object]` to `list[Asset]` in Step
        4.1 (API Foundation), its first real consumer (GET /v1/assets).
        """
        ...

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
    ) -> list[OHLCVBar]:
        """Most recent `limit` bars for (asset_id, interval), oldest -> newest.

        Implemented in Step 2.4 for MarketDataView.latest_bars — the first
        real consumer of this previously-stubbed method (see
        get_latest_ts's docstring: "get_bars() remains unimplemented
        pending a real consumer").
        """
        ...

    @abstractmethod
    async def get_bars_range(
        self, asset_id: UUID, interval: str, start: object, end: object
    ) -> list[OHLCVBar]:
        """All bars for (asset_id, interval) with start <= ts <= end, oldest -> newest.

        Added in Step 3.7 for the Backtesting Engine's historical replay
        (Doc 14 §10.3.4): a bounded chronological window, distinct from
        get_bars' "most recent N". `start`/`end` are timezone-aware datetimes.
        """
        ...

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
    async def get_latest(self, asset_id: UUID) -> Tick | None:
        """Most recently persisted tick for asset_id, or None.

        Implemented in Step 2.4 for MarketDataView.latest_tick — the
        first real consumer of this previously-stubbed method.
        """
        ...

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


class CorporateActionsRepository(ABC):
    """Persistence contract for market_data.corporate_actions — Doc 07 §Implementation Rules.

    Added in Step 1.10 for Doc 11 §3 Corporate Actions Processing.
    """

    @abstractmethod
    async def get_by_asset(self, asset_id: UUID) -> list[object]: ...

    @abstractmethod
    async def upsert_actions(self, actions: list[CorporateAction]) -> int:
        """Idempotently persist corporate actions, returning the count written.

        Idempotent on corporate_actions_asset_type_exdate_uq (migration
        97e88a746f25, Step 1.10) per Doc 11 §2 Requirements ("Idempotent
        ingestion") — proactively added before this repository existed,
        following the same precedent as the Step 1.2 tick-idempotency
        follow-up (migration a428732d6bfe). This UNIQUE constraint is also
        the mechanism behind Doc 11 §7 "Prevent duplicate publication" for
        corporate actions. See that migration for the residual
        same-ex-date-same-type collision limitation this key does not
        close.

        Doc 11 §3 Rules: "Original raw values remain preserved" — this
        method never writes to market_data.ohlcv_bars; it only records
        the corporate-action fact itself. Retroactively applying a split/
        dividend adjustment to historical bars is explicitly NOT
        implemented (Step 1.10 scope note, application service).
        """
        ...


class FundingRateRepository(ABC):
    """Persistence contract for market_data.funding_rates — perpetual funding
    observations (migration e7a3c1f5b9d2, Step 2 of perpetuals work).

    Follows the OHLCVRepository shape: idempotent batch write + a bounded
    read for the consuming strategy. Kept separate from OHLCV/tick repos
    because funding is a distinct perpetual-only data series (mirrors how
    CorporateActionsRepository is separate).
    """

    @abstractmethod
    async def upsert_funding_rates(self, rates: list[FundingRate]) -> int:
        """Idempotently persist funding observations, returning the count written.

        Idempotent on funding_rates_asset_funding_time_uq (asset_id,
        funding_time) per Doc 11 §2 ("Idempotent ingestion") — re-fetching a
        funding window revises rather than duplicates, the same pattern as
        upsert_bars.
        """
        ...

    @abstractmethod
    async def get_funding_rates(
        self, asset_id: UUID, limit: int = 100
    ) -> list[FundingRate]:
        """Most recent `limit` funding rows for asset_id, oldest -> newest.

        The read the funding-rate strategy (Step 4) consumes — same
        most-recent-N-then-chronological contract as OHLCVRepository.get_bars.
        """
        ...

    @abstractmethod
    async def get_latest_ts(self, asset_id: UUID) -> datetime | None:
        """Most recent persisted funding_time for asset_id, or None — the
        late-arrival/ingestion watermark, mirroring OHLCVRepository.get_latest_ts.
        """
        ...


class OpenInterestRepository(ABC):
    """Persistence contract for market_data.open_interest — perpetual open-
    interest observations (migration b4f8e21ac9d3).

    Follows FundingRateRepository's shape exactly: idempotent batch write +
    a bounded chronological read. Kept separate from OHLCV/tick/funding repos
    for the same reason FundingRateRepository is separate — OI is a distinct
    perpetual-only data series.
    """

    @abstractmethod
    async def upsert_open_interest(self, rows: list[OpenInterest]) -> int:
        """Idempotently persist OI observations, returning the count written.

        Idempotent on the (asset_id, ts) PRIMARY KEY per Doc 11 §2
        ("Idempotent ingestion") — re-fetching an OI window revises rather
        than duplicates, the same pattern as upsert_funding_rates/upsert_bars.
        """
        ...

    @abstractmethod
    async def get_open_interest_history(
        self, asset_id: UUID, limit: int = 100
    ) -> list[OpenInterest]:
        """Most recent `limit` OI rows for asset_id, oldest -> newest — same
        most-recent-N-then-chronological contract as get_funding_rates/get_bars.
        """
        ...

    @abstractmethod
    async def get_latest_ts(self, asset_id: UUID) -> datetime | None:
        """Most recent persisted ts for asset_id, or None — the late-arrival/
        ingestion watermark, mirroring FundingRateRepository.get_latest_ts.
        """
        ...

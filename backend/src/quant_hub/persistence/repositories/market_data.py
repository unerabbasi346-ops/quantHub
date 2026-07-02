# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Persistence — Doc 07 §Layers
# Repository pattern: concrete SQLAlchemy implementation — Doc 07 §Implementation Rules
# Dependency rule: infrastructure implements domain interfaces — Doc 07 §Dependency Rules
# Per Doc 00 §14.11
#
# Step 1.3: real writes for the upsert/save methods added in Step 1.2. No
# SQLAlchemy ORM models exist yet for market_data.* (Step 1.1 shipped
# raw-SQL Alembic DDL only, target_metadata=None in env.py — Doc 09
# §Migration Strategy) so these queries are hand-written parameterized SQL
# via sqlalchemy.text(), executed on the injected AsyncSession
# (BaseRepository, Step 0.4) — the same raw-SQL-first approach the Step 1.1
# migration and its Step 1.2 follow-up (a428732d6bfe) already established
# for this schema. Introducing ORM models here would be an architectural
# addition beyond "replace the stubs" and is not attempted (Doc 00 §14.6).
#
# JUDGMENT CALL (Doc 00 §14.5/§14.7 — flagged, not silently decided): none
# of these methods commit the session. Doc 07 §Implementation Rules gives
# the application/API layer (via api/dependencies.py's get_session, Step
# 0.4) ownership of transaction boundaries; a repository method that
# commits internally would take that decision away from its caller. Tests
# below commit explicitly where they need durability to assert against.
from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from quant_hub.domain.market_data.entities import AssetRef, OHLCVBar, Tick
from quant_hub.domain.market_data.interfaces import (
    AssetRepository,
    OHLCVRepository,
    TickRepository,
)
from quant_hub.persistence.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class SQLAlchemyAssetRepository(BaseRepository[object], AssetRepository):
    """Concrete repository for market_data.assets — Doc 07 §Implementation Rules."""

    async def get_by_id(self, asset_id: UUID) -> object | None:
        return None  # stub: SQLAlchemy query in Step 0.5+

    async def get_by_symbol_exchange(self, symbol: str, exchange: str) -> object | None:
        return None  # stub

    async def list_active(self) -> list[object]:
        return []  # stub

    async def upsert(self, asset: AssetRef) -> UUID:
        """Resolve-or-create on assets_symbol_exchange_uq — Doc 11 §2 idempotent ingestion.

        ON CONFLICT DO UPDATE (rather than DO NOTHING) so that a re-ingested
        asset's name/asset_class/currency can drift toward the latest
        connector-reported value instead of freezing at first-seen state —
        the interface docstring (domain/market_data/interfaces.py) only
        requires "resolve-or-create", not "first write wins"; DO UPDATE is
        the interpretation that keeps the row live, matching Doc 11's
        general idempotent-ingestion intent. Flagged since Doc 11 does not
        state this explicitly either way.

        `id` and `created_at` are deliberately absent from SET (Doc 09
        entity-standard: created_at is immutable once written). `updated_at`
        uses clock_timestamp(), not NOW(): NOW() is frozen at transaction
        start, so two upserts to the same row inside one caller-owned
        transaction (Doc 07 — repositories don't commit) would otherwise
        write an identical, stale updated_at on the second write.
        """
        stmt = text(
            """
            INSERT INTO market_data.assets (symbol, exchange, asset_class, name, currency)
            VALUES (:symbol, :exchange, :asset_class, :name, :currency)
            ON CONFLICT ON CONSTRAINT assets_symbol_exchange_uq
            DO UPDATE SET
                asset_class = EXCLUDED.asset_class,
                name        = EXCLUDED.name,
                currency    = EXCLUDED.currency,
                updated_at  = clock_timestamp()
            RETURNING id
            """
        )
        result = await self._session.execute(
            stmt,
            {
                "symbol": asset.symbol,
                "exchange": asset.exchange,
                "asset_class": asset.asset_class,
                "name": asset.name,
                "currency": asset.currency,
            },
        )
        return result.scalar_one()


class SQLAlchemyOHLCVRepository(BaseRepository[object], OHLCVRepository):
    """Concrete repository for market_data.ohlcv_bars."""

    async def get_bars(self, asset_id: UUID, interval: str, limit: int = 100) -> list[object]:
        return []  # stub

    async def upsert_bars(self, bars: list[OHLCVBar]) -> int:
        """Idempotently persist bars on ohlcv_bars_asset_interval_ts_uq — Doc 11 §2.

        ON CONFLICT DO UPDATE on the OHLCV fields: a re-ingested bar for the
        same (asset_id, interval, ts) most often means a vendor correction
        (e.g. a previously-partial bar finalizing) or a backfill overlapping
        live data, so the latest write should replace the stored values
        rather than being dropped — same DO-UPDATE reasoning as
        AssetRepository.upsert above, flagged for the same reason (Doc 11
        does not state a conflict-resolution policy explicitly).

        Executes one statement per bar rather than a single multi-row
        INSERT: bars is caller-supplied and unbounded, and asyncpg/psycopg
        parameter-count limits make a single giant multi-row statement
        fragile at scale. Doc 11 does not mandate a batching strategy, so
        this per-row loop is the simplest correct implementation.
        REVISIT TRIGGER (Doc 00 §14.5 — explicit, not open-ended): switch to
        batched multi-row INSERT ... ON CONFLICT before Phase 1 historical
        backfill work begins (backfills are the workload that pushes a
        single ingestion call from tens of bars to thousands+, where
        per-row round-trips dominate latency), or immediately if any single
        upsert_bars() call is observed/expected to carry more than ~500
        bars, whichever comes first.

        `id`/`created_at` excluded from SET and `updated_at` uses
        clock_timestamp() rather than NOW() for the same reason as
        AssetRepository.upsert above (NOW() is frozen for the lifetime of
        the caller's transaction).

        CHECKPOINT RECOVERY (Step 1.8, Doc 11 §8 Error Recovery, scoped per
        S-2): each bar's INSERT runs inside its own SAVEPOINT
        (session.begin_nested()). In Postgres, one failing statement
        aborts the whole enclosing transaction — without a SAVEPOINT, bar
        15 of 24 failing would poison bars 1-14's already-executed (but
        not yet committed, since repositories don't commit — see module
        docstring) work too, and every subsequent statement in the same
        transaction would also fail. Rolling back to the SAVEPOINT on
        failure clears just that bar's error, leaving the transaction
        (and bars 1-14) intact for the caller's eventual commit. The
        failing bar is logged (not silently dropped, per Doc 11 §8) and
        excluded from the returned count; the loop continues.
        """
        stmt = text(
            """
            INSERT INTO market_data.ohlcv_bars
                (asset_id, interval, ts, open, high, low, close, volume,
                 vwap, trade_count, adjustment_factor, data_quality, source)
            VALUES
                (:asset_id, :interval, :ts, :open, :high, :low, :close, :volume,
                 :vwap, :trade_count, :adjustment_factor, :data_quality, :source)
            ON CONFLICT ON CONSTRAINT ohlcv_bars_asset_interval_ts_uq
            DO UPDATE SET
                open              = EXCLUDED.open,
                high              = EXCLUDED.high,
                low               = EXCLUDED.low,
                close             = EXCLUDED.close,
                volume            = EXCLUDED.volume,
                vwap              = EXCLUDED.vwap,
                trade_count       = EXCLUDED.trade_count,
                adjustment_factor = EXCLUDED.adjustment_factor,
                data_quality      = EXCLUDED.data_quality,
                source            = EXCLUDED.source,
                updated_at        = clock_timestamp()
            """
        )
        count = 0
        for bar in bars:
            try:
                async with self._session.begin_nested():
                    await self._session.execute(
                        stmt,
                        {
                            "asset_id": bar.asset_id,
                            "interval": bar.interval,
                            "ts": bar.ts,
                            "open": bar.open,
                            "high": bar.high,
                            "low": bar.low,
                            "close": bar.close,
                            "volume": bar.volume,
                            "vwap": bar.vwap,
                            "trade_count": bar.trade_count,
                            "adjustment_factor": bar.adjustment_factor,
                            "data_quality": bar.data_quality,
                            "source": bar.source,
                        },
                    )
                count += 1
            except DBAPIError as exc:
                logger.error(
                    "upsert_bars: failed to persist bar, asset_id=%s interval=%s "
                    "ts=%s error=%r",
                    bar.asset_id, bar.interval, bar.ts, exc,
                )
        return count


class SQLAlchemyTickRepository(BaseRepository[object], TickRepository):
    """Concrete repository for market_data.ticks."""

    async def get_latest(self, asset_id: UUID) -> object | None:
        return None  # stub

    async def save_tick(self, tick: Tick) -> None:
        """Idempotently append a tick — Doc 11 §2, resolved via migration a428732d6bfe.

        Uses ON CONFLICT (asset_id, ts, feed_origin) DO NOTHING per that
        migration's explicit "Consequence for callers" note: ticks are
        append-only (Doc 11 §7), so — unlike assets/bars above — a
        conflicting retry should be silently absorbed rather than updating
        the existing row; there is no "correction" semantic for a tick the
        way there is for a bar.
        """
        stmt = text(
            """
            INSERT INTO market_data.ticks
                (asset_id, ts, received_at, feed_origin, bid, ask, last,
                 bid_size, ask_size, last_size, volume, conditions,
                 data_quality, sequence_num)
            VALUES
                (:asset_id, :ts, :received_at, :feed_origin, :bid, :ask, :last,
                 :bid_size, :ask_size, :last_size, :volume, :conditions,
                 :data_quality, :sequence_num)
            ON CONFLICT ON CONSTRAINT ticks_asset_ts_feed_origin_uq
            DO NOTHING
            """
        )
        await self._session.execute(
            stmt,
            {
                "asset_id": tick.asset_id,
                "ts": tick.ts,
                "received_at": tick.received_at,
                "feed_origin": tick.feed_origin,
                "bid": tick.bid,
                "ask": tick.ask,
                "last": tick.last,
                "bid_size": tick.bid_size,
                "ask_size": tick.ask_size,
                "last_size": tick.last_size,
                "volume": tick.volume,
                "conditions": list(tick.conditions),
                "data_quality": tick.data_quality,
                "sequence_num": tick.sequence_num,
            },
        )

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
from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from quant_hub.domain.market_data.entities import AssetRef, CorporateAction, OHLCVBar, Tick
from quant_hub.domain.market_data.interfaces import (
    AssetRepository,
    CorporateActionsRepository,
    OHLCVRepository,
    TickRepository,
)
from quant_hub.persistence.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class SQLAlchemyAssetRepository(BaseRepository[object], AssetRepository):
    """Concrete repository for market_data.assets — Doc 07 §Implementation Rules."""

    async def get_by_id(self, asset_id: UUID) -> object | None:
        return None  # stub: SQLAlchemy query in Step 0.5+

    async def get_by_symbol_exchange(self, symbol: str, exchange: str) -> UUID | None:
        """Resolve-only lookup on assets_symbol_exchange_uq — Step 2.4,
        first real consumer: MarketDataView's AssetRef -> asset_id
        resolution (infrastructure/strategy_engine/market_data_view.py).
        Returns None (not an error) for an unregistered asset — the
        caller decides what "no data" means for its use case.
        """
        result = await self._session.execute(
            text(
                "SELECT id FROM market_data.assets "
                "WHERE symbol = :symbol AND exchange = :exchange AND deleted_at IS NULL"
            ),
            {"symbol": symbol, "exchange": exchange},
        )
        return result.scalar_one_or_none()

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

    async def get_bars(self, asset_id: UUID, interval: str, limit: int = 100) -> list[OHLCVBar]:
        """Most recent `limit` bars for (asset_id, interval), oldest -> newest —
        Step 2.4, first real consumer: MarketDataView.latest_bars.

        Queries ORDER BY ts DESC LIMIT :limit (cheapest way to get the
        most-recent N rows), then reverses to oldest -> newest before
        returning — MarketDataView's documented contract (Step 2.1) — so a
        caller doing a moving-average-style computation over the result
        doesn't have to remember to reverse it itself.
        """
        result = await self._session.execute(
            text(
                """
                SELECT asset_id, interval, ts, open, high, low, close, volume,
                       vwap, trade_count, adjustment_factor, data_quality, source
                FROM market_data.ohlcv_bars
                WHERE asset_id = :asset_id AND interval = :interval
                ORDER BY ts DESC
                LIMIT :limit
                """
            ),
            {"asset_id": asset_id, "interval": interval, "limit": limit},
        )
        rows = result.mappings().all()
        return [
            OHLCVBar(
                asset_id=row["asset_id"],
                interval=row["interval"],
                ts=row["ts"],
                open=row["open"],
                high=row["high"],
                low=row["low"],
                close=row["close"],
                volume=row["volume"],
                vwap=row["vwap"],
                trade_count=row["trade_count"],
                adjustment_factor=row["adjustment_factor"],
                data_quality=row["data_quality"],
                source=row["source"],
            )
            for row in reversed(rows)
        ]

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

        VERSION HISTORY (Step 1.9, Doc 11 §7 "Maintain dataset version
        history", scoped per S-2 — see handbook/KNOWN_LIMITATIONS.md S-3
        for the full judgment call): `updated_at` (clock_timestamp() on
        every write, above) tells a reader THAT and WHEN a bar changed,
        but not WHAT changed. As a lightweight addition — not a full
        versioned/immutable dataset system (Part 4, out of scope per S-1)
        — each write reports via Postgres' `xmax = 0` idiom (true only for
        a row inserted, not updated, by the current command) whether it
        was a fresh insert or a revision of an existing bar; the batch
        logs an insert/revised summary at INFO level rather than
        persisting a separate audit table.
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
            RETURNING (xmax = 0) AS was_insert
            """
        )
        inserted = 0
        revised = 0
        failed = 0
        for bar in bars:
            try:
                async with self._session.begin_nested():
                    result = await self._session.execute(
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
                if result.scalar_one():
                    inserted += 1
                else:
                    revised += 1
            except DBAPIError as exc:
                failed += 1
                logger.error(
                    "upsert_bars: failed to persist bar, asset_id=%s interval=%s "
                    "ts=%s error=%r",
                    bar.asset_id, bar.interval, bar.ts, exc,
                )
        if bars:
            logger.info(
                "upsert_bars: batch summary asset_id=%s interval=%s "
                "inserted=%d revised=%d failed=%d",
                bars[0].asset_id, bars[0].interval, inserted, revised, failed,
            )
        return inserted + revised

    async def get_latest_ts(self, asset_id: UUID, interval: str) -> datetime | None:
        """Doc 11 §7 late-arrival-detection watermark — see interface docstring."""
        result = await self._session.execute(
            text(
                "SELECT MAX(ts) FROM market_data.ohlcv_bars "
                "WHERE asset_id = :asset_id AND interval = :interval"
            ),
            {"asset_id": asset_id, "interval": interval},
        )
        return result.scalar_one_or_none()


class SQLAlchemyTickRepository(BaseRepository[object], TickRepository):
    """Concrete repository for market_data.ticks."""

    async def get_latest(self, asset_id: UUID) -> Tick | None:
        """Most recent persisted tick for asset_id — Step 2.4, first real
        consumer: MarketDataView.latest_tick."""
        result = await self._session.execute(
            text(
                """
                SELECT asset_id, ts, received_at, feed_origin, bid, ask, last,
                       bid_size, ask_size, last_size, volume, conditions,
                       data_quality, sequence_num
                FROM market_data.ticks
                WHERE asset_id = :asset_id
                ORDER BY ts DESC
                LIMIT 1
                """
            ),
            {"asset_id": asset_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            return None
        return Tick(
            asset_id=row["asset_id"],
            ts=row["ts"],
            received_at=row["received_at"],
            feed_origin=row["feed_origin"],
            bid=row["bid"],
            ask=row["ask"],
            last=row["last"],
            bid_size=row["bid_size"],
            ask_size=row["ask_size"],
            last_size=row["last_size"],
            volume=row["volume"],
            conditions=tuple(row["conditions"] or ()),
            data_quality=row["data_quality"],
            sequence_num=row["sequence_num"],
        )

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

    async def get_latest_ts(self, asset_id: UUID) -> datetime | None:
        """Doc 11 §7 late-arrival-detection watermark — see interface docstring.

        JUDGMENT CALL: scoped to asset_id only, not (asset_id,
        feed_origin) — every current connector maps 1:1 to a single feed
        per asset, so the extra dimension isn't yet meaningful. Revisit if
        an asset is ever ingested from multiple concurrent tick feeds.
        """
        result = await self._session.execute(
            text("SELECT MAX(ts) FROM market_data.ticks WHERE asset_id = :asset_id"),
            {"asset_id": asset_id},
        )
        return result.scalar_one_or_none()


class SQLAlchemyCorporateActionsRepository(BaseRepository[object], CorporateActionsRepository):
    """Concrete repository for market_data.corporate_actions — Step 1.10, Doc 11 §3."""

    async def get_by_asset(self, asset_id: UUID) -> list[object]:
        return []  # stub — SQLAlchemy query pending a real consumer, same as get_bars/get_latest

    async def upsert_actions(self, actions: list[CorporateAction]) -> int:
        """Idempotently persist corporate actions on
        corporate_actions_asset_type_exdate_uq — Doc 11 §2/§3, migration
        97e88a746f25 (Step 1.10).

        ON CONFLICT DO UPDATE, checkpoint isolation (SAVEPOINT per row),
        and the insert/revised tally all follow the exact same pattern as
        SQLAlchemyOHLCVRepository.upsert_bars above — see that method's
        docstring for the full reasoning (DO-UPDATE-vs-DO-NOTHING
        judgment call, per-row SAVEPOINT rationale, xmax=0 version-history
        signal). Reused here rather than re-derived, per Doc 11 §3 Rules
        "Original raw values remain preserved": this method only ever
        writes to market_data.corporate_actions, never to
        market_data.ohlcv_bars, so the raw OHLCV data is untouched by
        definition, not by a special case in this code.
        """
        stmt = text(
            """
            INSERT INTO market_data.corporate_actions
                (asset_id, action_type, ex_date, record_date, payment_date,
                 ratio, amount, currency, notes)
            VALUES
                (:asset_id, :action_type, :ex_date, :record_date, :payment_date,
                 :ratio, :amount, :currency, :notes)
            ON CONFLICT ON CONSTRAINT corporate_actions_asset_type_exdate_uq
            DO UPDATE SET
                record_date  = EXCLUDED.record_date,
                payment_date = EXCLUDED.payment_date,
                ratio        = EXCLUDED.ratio,
                amount       = EXCLUDED.amount,
                currency     = EXCLUDED.currency,
                notes        = EXCLUDED.notes,
                updated_at   = clock_timestamp()
            RETURNING (xmax = 0) AS was_insert
            """
        )
        inserted = 0
        revised = 0
        failed = 0
        for action in actions:
            try:
                async with self._session.begin_nested():
                    result = await self._session.execute(
                        stmt,
                        {
                            "asset_id": action.asset_id,
                            "action_type": action.action_type,
                            "ex_date": action.ex_date,
                            "record_date": action.record_date,
                            "payment_date": action.payment_date,
                            "ratio": action.ratio,
                            "amount": action.amount,
                            "currency": action.currency,
                            "notes": action.notes,
                        },
                    )
                if result.scalar_one():
                    inserted += 1
                else:
                    revised += 1
            except DBAPIError as exc:
                failed += 1
                logger.error(
                    "upsert_actions: failed to persist corporate action, asset_id=%s "
                    "action_type=%s ex_date=%s error=%r",
                    action.asset_id, action.action_type, action.ex_date, exc,
                )
        if actions:
            logger.info(
                "upsert_actions: batch summary asset_id=%s inserted=%d revised=%d failed=%d",
                actions[0].asset_id, inserted, revised, failed,
            )
        return inserted + revised

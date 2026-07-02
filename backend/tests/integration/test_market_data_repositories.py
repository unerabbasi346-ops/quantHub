# Governing specification: Doc 11 — Data Engineering (§2 Idempotent ingestion)
#                          Doc 09 — Database Architecture (Step 1.1/1.2 migrations)
# Per Doc 00 §14.11
#
# Exercises the Step 1.3 repository implementations
# (persistence/repositories/market_data.py) against a live Postgres with
# both migrations applied (c3a8f2b91e4d, a428732d6bfe). Each ABC method's
# tests cover: (a) a fresh write succeeds, (b) a duplicate write is
# absorbed/updated per that method's documented conflict strategy, (c)
# repeated/concurrent identical writes cause no corruption (extra rows,
# lost updates, or errors).
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from quant_hub.config import settings
from quant_hub.domain.market_data.entities import AssetRef, OHLCVBar, Tick
from quant_hub.persistence.repositories.market_data import (
    SQLAlchemyAssetRepository,
    SQLAlchemyOHLCVRepository,
    SQLAlchemyTickRepository,
)


def _unique_symbol(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ---------------------------------------------------------------------------
# AssetRepository.upsert
# ---------------------------------------------------------------------------


async def test_asset_upsert_fresh_insert_succeeds(db_session: AsyncSession) -> None:
    repo = SQLAlchemyAssetRepository(db_session)
    ref = AssetRef(symbol=_unique_symbol("TST"), exchange="TESTX", asset_class="equity")

    asset_id = await repo.upsert(ref)

    assert isinstance(asset_id, uuid.UUID)
    row = (
        await db_session.execute(
            text(
                "SELECT symbol, exchange, asset_class FROM market_data.assets WHERE id = :id"
            ),
            {"id": asset_id},
        )
    ).one()
    assert (row.symbol, row.exchange, row.asset_class) == (ref.symbol, ref.exchange, "equity")


async def test_asset_upsert_duplicate_updates_existing_row(db_session: AsyncSession) -> None:
    repo = SQLAlchemyAssetRepository(db_session)
    symbol = _unique_symbol("TST")
    first = AssetRef(symbol=symbol, exchange="TESTX", asset_class="equity", name="First")
    second = AssetRef(symbol=symbol, exchange="TESTX", asset_class="equity", name="Second")

    id1 = await repo.upsert(first)
    id2 = await repo.upsert(second)

    assert id1 == id2
    count = (
        await db_session.execute(
            text(
                "SELECT COUNT(*) FROM market_data.assets WHERE symbol = :s AND exchange = :e"
            ),
            {"s": symbol, "e": "TESTX"},
        )
    ).scalar_one()
    assert count == 1
    name = (
        await db_session.execute(
            text("SELECT name FROM market_data.assets WHERE id = :id"), {"id": id1}
        )
    ).scalar_one()
    assert name == "Second"


async def test_asset_upsert_repeated_identical_calls_no_corruption(
    db_session: AsyncSession,
) -> None:
    repo = SQLAlchemyAssetRepository(db_session)
    ref = AssetRef(symbol=_unique_symbol("TST"), exchange="TESTX", asset_class="equity")

    ids = [await repo.upsert(ref) for _ in range(5)]

    assert len(set(ids)) == 1
    count = (
        await db_session.execute(
            text(
                "SELECT COUNT(*) FROM market_data.assets WHERE symbol = :s AND exchange = :e"
            ),
            {"s": ref.symbol, "e": ref.exchange},
        )
    ).scalar_one()
    assert count == 1


# ---------------------------------------------------------------------------
# OHLCVRepository.upsert_bars
# ---------------------------------------------------------------------------


def _bar(asset_id: uuid.UUID, ts: datetime, close: Decimal) -> OHLCVBar:
    return OHLCVBar(
        asset_id=asset_id,
        interval="1d",
        ts=ts,
        open=Decimal("100.00000000"),
        high=Decimal("110.00000000"),
        low=Decimal("95.00000000"),
        close=close,
        volume=1000,
        source="testsrc",
    )


async def test_ohlcv_upsert_bars_fresh_insert_succeeds(db_session: AsyncSession) -> None:
    assets = SQLAlchemyAssetRepository(db_session)
    ohlcv = SQLAlchemyOHLCVRepository(db_session)
    asset_id = await assets.upsert(
        AssetRef(symbol=_unique_symbol("BAR"), exchange="TESTX", asset_class="equity")
    )
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc)

    written = await ohlcv.upsert_bars([_bar(asset_id, ts, Decimal("105.00000000"))])

    assert written == 1
    row = (
        await db_session.execute(
            text(
                "SELECT close FROM market_data.ohlcv_bars "
                "WHERE asset_id = :aid AND interval = '1d' AND ts = :ts"
            ),
            {"aid": asset_id, "ts": ts},
        )
    ).one()
    assert row.close == Decimal("105.00000000")


async def test_ohlcv_upsert_bars_duplicate_updates_existing_row(
    db_session: AsyncSession,
) -> None:
    assets = SQLAlchemyAssetRepository(db_session)
    ohlcv = SQLAlchemyOHLCVRepository(db_session)
    asset_id = await assets.upsert(
        AssetRef(symbol=_unique_symbol("BAR"), exchange="TESTX", asset_class="equity")
    )
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc)

    await ohlcv.upsert_bars([_bar(asset_id, ts, Decimal("105.00000000"))])
    written_again = await ohlcv.upsert_bars([_bar(asset_id, ts, Decimal("999.00000000"))])

    assert written_again == 1
    count, close = (
        await db_session.execute(
            text(
                "SELECT COUNT(*), MAX(close) FROM market_data.ohlcv_bars "
                "WHERE asset_id = :aid AND interval = '1d' AND ts = :ts"
            ),
            {"aid": asset_id, "ts": ts},
        )
    ).one()
    assert count == 1
    assert close == Decimal("999.00000000")


async def test_ohlcv_upsert_bars_repeated_identical_calls_no_corruption(
    db_session: AsyncSession,
) -> None:
    assets = SQLAlchemyAssetRepository(db_session)
    ohlcv = SQLAlchemyOHLCVRepository(db_session)
    asset_id = await assets.upsert(
        AssetRef(symbol=_unique_symbol("BAR"), exchange="TESTX", asset_class="equity")
    )
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    bar = _bar(asset_id, ts, Decimal("105.00000000"))

    for _ in range(5):
        await ohlcv.upsert_bars([bar])

    count = (
        await db_session.execute(
            text(
                "SELECT COUNT(*) FROM market_data.ohlcv_bars "
                "WHERE asset_id = :aid AND interval = '1d' AND ts = :ts"
            ),
            {"aid": asset_id, "ts": ts},
        )
    ).scalar_one()
    assert count == 1


async def test_ohlcv_upsert_bars_isolates_mid_batch_failure(db_session: AsyncSession) -> None:
    """Doc 11 §8 Error Recovery (Step 1.8), scoped per S-2: a real
    foreign-key violation on one bar (a nonexistent asset_id) must not
    poison bars before or after it in the same upsert_bars() call —
    proves the per-bar SAVEPOINT checkpoint isolation, not just that a
    single insert works."""
    assets = SQLAlchemyAssetRepository(db_session)
    ohlcv = SQLAlchemyOHLCVRepository(db_session)
    asset_id = await assets.upsert(
        AssetRef(symbol=_unique_symbol("CHKPT"), exchange="TESTX", asset_class="crypto")
    )
    fake_asset_id = uuid.uuid4()  # not present in market_data.assets

    def bar_at(asset: uuid.UUID, hour: int) -> OHLCVBar:
        return _bar(asset, datetime(2026, 1, 1, hour, tzinfo=timezone.utc), Decimal("100"))

    batch = [
        bar_at(asset_id, 0),  # before the failure
        bar_at(asset_id, 1),  # before the failure
        bar_at(fake_asset_id, 2),  # FK violation
        bar_at(asset_id, 3),  # after the failure
    ]

    count = await ohlcv.upsert_bars(batch)

    assert count == 3  # 3 of 4 persisted; the FK-violating bar excluded
    rows = (
        await db_session.execute(
            text(
                "SELECT ts FROM market_data.ohlcv_bars WHERE asset_id = :aid ORDER BY ts"
            ),
            {"aid": asset_id},
        )
    ).all()
    assert [r.ts.hour for r in rows] == [0, 1, 3]


async def test_ohlcv_get_latest_ts_reflects_persisted_bars(db_session: AsyncSession) -> None:
    """Doc 11 §7 late-arrival-detection watermark (Step 1.9)."""
    assets = SQLAlchemyAssetRepository(db_session)
    ohlcv = SQLAlchemyOHLCVRepository(db_session)
    asset_id = await assets.upsert(
        AssetRef(symbol=_unique_symbol("WTRMRK"), exchange="TESTX", asset_class="crypto")
    )

    assert await ohlcv.get_latest_ts(asset_id, "1d") is None  # nothing persisted yet

    ts1 = datetime(2026, 1, 1, 0, tzinfo=timezone.utc)
    ts2 = datetime(2026, 1, 1, 5, tzinfo=timezone.utc)
    await ohlcv.upsert_bars([_bar(asset_id, ts1, Decimal("1")), _bar(asset_id, ts2, Decimal("2"))])

    assert await ohlcv.get_latest_ts(asset_id, "1d") == ts2  # MAX(ts), not last-inserted


async def test_ohlcv_upsert_bars_reports_insert_vs_revised_counts(
    db_session: AsyncSession, caplog
) -> None:
    """Doc 11 §7 minimal version-history signal (Step 1.9, S-3): the batch
    summary log distinguishes fresh inserts from revisions of existing bars."""
    import logging

    assets = SQLAlchemyAssetRepository(db_session)
    ohlcv = SQLAlchemyOHLCVRepository(db_session)
    asset_id = await assets.upsert(
        AssetRef(symbol=_unique_symbol("VERHIST"), exchange="TESTX", asset_class="crypto")
    )
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc)

    with caplog.at_level(logging.INFO):
        await ohlcv.upsert_bars([_bar(asset_id, ts, Decimal("100"))])  # fresh insert
        await ohlcv.upsert_bars([_bar(asset_id, ts, Decimal("999"))])  # revision

    summaries = [r.getMessage() for r in caplog.records if "batch summary" in r.getMessage()]
    assert len(summaries) == 2
    assert "inserted=1 revised=0 failed=0" in summaries[0]
    assert "inserted=0 revised=1 failed=0" in summaries[1]


# ---------------------------------------------------------------------------
# TickRepository.save_tick
# ---------------------------------------------------------------------------


def _tick(asset_id: uuid.UUID, ts: datetime) -> Tick:
    now = datetime.now(timezone.utc)
    return Tick(
        asset_id=asset_id,
        ts=ts,
        received_at=now,
        feed_origin="testfeed",
        last=Decimal("42.50000000"),
    )


async def test_tick_save_fresh_insert_succeeds(db_session: AsyncSession) -> None:
    assets = SQLAlchemyAssetRepository(db_session)
    ticks = SQLAlchemyTickRepository(db_session)
    asset_id = await assets.upsert(
        AssetRef(symbol=_unique_symbol("TIK"), exchange="TESTX", asset_class="crypto")
    )
    ts = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    await ticks.save_tick(_tick(asset_id, ts))

    row = (
        await db_session.execute(
            text(
                "SELECT last FROM market_data.ticks "
                "WHERE asset_id = :aid AND ts = :ts AND feed_origin = 'testfeed'"
            ),
            {"aid": asset_id, "ts": ts},
        )
    ).one()
    assert row.last == Decimal("42.50000000")


async def test_tick_save_duplicate_is_absorbed_not_duplicated(
    db_session: AsyncSession,
) -> None:
    assets = SQLAlchemyAssetRepository(db_session)
    ticks = SQLAlchemyTickRepository(db_session)
    asset_id = await assets.upsert(
        AssetRef(symbol=_unique_symbol("TIK"), exchange="TESTX", asset_class="crypto")
    )
    ts = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    tick = _tick(asset_id, ts)

    await ticks.save_tick(tick)
    await ticks.save_tick(tick)  # retry of the exact same tick — must not raise

    count = (
        await db_session.execute(
            text(
                "SELECT COUNT(*) FROM market_data.ticks "
                "WHERE asset_id = :aid AND ts = :ts AND feed_origin = 'testfeed'"
            ),
            {"aid": asset_id, "ts": ts},
        )
    ).scalar_one()
    assert count == 1


async def test_tick_save_repeated_identical_calls_no_corruption(
    db_session: AsyncSession,
) -> None:
    assets = SQLAlchemyAssetRepository(db_session)
    ticks = SQLAlchemyTickRepository(db_session)
    asset_id = await assets.upsert(
        AssetRef(symbol=_unique_symbol("TIK"), exchange="TESTX", asset_class="crypto")
    )
    ts = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    tick = _tick(asset_id, ts)

    for _ in range(5):
        await ticks.save_tick(tick)

    count = (
        await db_session.execute(
            text(
                "SELECT COUNT(*) FROM market_data.ticks "
                "WHERE asset_id = :aid AND ts = :ts AND feed_origin = 'testfeed'"
            ),
            {"aid": asset_id, "ts": ts},
        )
    ).scalar_one()
    assert count == 1


# ---------------------------------------------------------------------------
# True concurrency (separate connections/transactions, real commits)
#
# JUDGMENT CALL (Doc 00 §14.5/§14.7 — flagged): the db_session fixture
# above gives each test one connection/transaction, which cannot exercise
# genuine concurrent writers racing at the database level. The two tests
# below use independent engines/sessions with real commits instead of the
# shared rolled-back fixture, and clean up via explicit DELETE. Run for
# AssetRepository.upsert and TickRepository.save_tick as representative
# cases (INSERT ... ON CONFLICT DO UPDATE and DO NOTHING respectively); a
# third concurrent test for OHLCVRepository.upsert_bars would exercise the
# identical ON CONFLICT DO UPDATE mechanism already covered by the asset
# case and is skipped to keep the suite reasonably scoped.
# ---------------------------------------------------------------------------


async def test_concurrent_asset_upsert_no_duplicate_rows(engine: AsyncEngine) -> None:
    symbol = _unique_symbol("CONC")
    ref = AssetRef(symbol=symbol, exchange="TESTX", asset_class="equity")

    async def do_upsert() -> uuid.UUID:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            asset_id = await SQLAlchemyAssetRepository(session).upsert(ref)
            await session.commit()
            return asset_id

    try:
        results = await asyncio.gather(*(do_upsert() for _ in range(8)))
        assert len(set(results)) == 1

        async with engine.connect() as conn:
            count = (
                await conn.execute(
                    text(
                        "SELECT COUNT(*) FROM market_data.assets "
                        "WHERE symbol = :s AND exchange = :e"
                    ),
                    {"s": symbol, "e": "TESTX"},
                )
            ).scalar_one()
            assert count == 1
    finally:
        async with engine.connect() as conn:
            await conn.execute(
                text(
                    "DELETE FROM market_data.assets WHERE symbol = :s AND exchange = :e"
                ),
                {"s": symbol, "e": "TESTX"},
            )
            await conn.commit()


async def test_concurrent_tick_save_no_duplicate_rows(engine: AsyncEngine) -> None:
    symbol = _unique_symbol("CONC")
    ts = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    async with AsyncSession(engine, expire_on_commit=False) as setup_session:
        asset_id = await SQLAlchemyAssetRepository(setup_session).upsert(
            AssetRef(symbol=symbol, exchange="TESTX", asset_class="crypto")
        )
        await setup_session.commit()

    async def do_save() -> None:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            await SQLAlchemyTickRepository(session).save_tick(_tick(asset_id, ts))
            await session.commit()

    try:
        await asyncio.gather(*(do_save() for _ in range(8)))

        async with engine.connect() as conn:
            count = (
                await conn.execute(
                    text(
                        "SELECT COUNT(*) FROM market_data.ticks "
                        "WHERE asset_id = :aid AND ts = :ts AND feed_origin = 'testfeed'"
                    ),
                    {"aid": asset_id, "ts": ts},
                )
            ).scalar_one()
            assert count == 1
    finally:
        async with engine.connect() as conn:
            await conn.execute(
                text("DELETE FROM market_data.ticks WHERE asset_id = :aid"),
                {"aid": asset_id},
            )
            await conn.execute(
                text("DELETE FROM market_data.assets WHERE id = :aid"),
                {"aid": asset_id},
            )
            await conn.commit()

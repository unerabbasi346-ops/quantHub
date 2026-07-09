# Governing specification: Doc 11 §2 (Idempotent ingestion); Doc 14 §10.9.5
#   (Financing Costs — the funding cashflow this data feeds)
#                          Doc 09 — migration e7a3c1f5b9d2 (market_data.funding_rates,
#   market_data.assets.instrument_type)
#                          handbook/KNOWN_LIMITATIONS.md S-10
# Per Doc 00 §14.11
#
# Exercises Step 2 of the perpetuals work against a live Postgres with
# migration e7a3c1f5b9d2 applied: (1) instrument_type persists and reads back
# through the asset repository (spot vs perpetual for the same underlying are
# distinct rows); (2) SQLAlchemyFundingRateRepository upsert idempotency,
# chronological read ordering, and the latest-ts watermark.
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from quant_hub.domain.market_data.entities import AssetRef, FundingRate
from quant_hub.persistence.repositories.market_data import (
    SQLAlchemyAssetRepository,
    SQLAlchemyFundingRateRepository,
)


def _unique_symbol(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ---------------------------------------------------------------------------
# market_data.assets.instrument_type round-trip
# ---------------------------------------------------------------------------


async def test_asset_upsert_persists_instrument_type(db_session: AsyncSession) -> None:
    repo = SQLAlchemyAssetRepository(db_session)
    perp = AssetRef(
        symbol=_unique_symbol("PERP"),
        exchange="TESTX",
        asset_class="crypto",
        instrument_type="PERPETUAL",
    )

    asset_id = await repo.upsert(perp)

    stored = (
        await db_session.execute(
            text("SELECT instrument_type FROM market_data.assets WHERE id = :id"),
            {"id": asset_id},
        )
    ).scalar_one()
    assert stored == "PERPETUAL"
    # and reads back through the typed read path
    read = await repo.get_by_id(asset_id)
    assert read is not None and read.instrument_type == "PERPETUAL"


async def test_asset_default_instrument_type_is_spot(db_session: AsyncSession) -> None:
    repo = SQLAlchemyAssetRepository(db_session)
    # AssetRef default instrument_type is SPOT — an unspecified caller gets spot.
    ref = AssetRef(symbol=_unique_symbol("SPT"), exchange="TESTX", asset_class="crypto")

    asset_id = await repo.upsert(ref)

    read = await repo.get_by_id(asset_id)
    assert read is not None and read.instrument_type == "SPOT"


async def test_spot_and_perp_same_underlying_are_distinct_rows(db_session: AsyncSession) -> None:
    # ccxt distinguishes them by symbol (BASE/QUOTE vs BASE/QUOTE:SETTLE), so
    # they resolve to two rows under assets_symbol_exchange_uq, not one.
    repo = SQLAlchemyAssetRepository(db_session)
    base = _unique_symbol("BTC")
    spot = AssetRef(symbol=base, exchange="TESTX", asset_class="crypto", instrument_type="SPOT")
    perp = AssetRef(
        symbol=f"{base}:USDT", exchange="TESTX", asset_class="crypto", instrument_type="PERPETUAL"
    )

    spot_id = await repo.upsert(spot)
    perp_id = await repo.upsert(perp)

    assert spot_id != perp_id


# ---------------------------------------------------------------------------
# SQLAlchemyFundingRateRepository
# ---------------------------------------------------------------------------


async def _make_perp_asset(db_session: AsyncSession) -> uuid.UUID:
    return await SQLAlchemyAssetRepository(db_session).upsert(
        AssetRef(
            symbol=_unique_symbol("PERP"),
            exchange="TESTX",
            asset_class="crypto",
            instrument_type="PERPETUAL",
        )
    )


def _rate(asset_id: uuid.UUID, ts: datetime, value: str) -> FundingRate:
    return FundingRate(
        asset_id=asset_id,
        funding_time=ts,
        funding_rate=Decimal(value),
        source="TESTX",
    )


async def test_funding_upsert_fresh_insert(db_session: AsyncSession) -> None:
    asset_id = await _make_perp_asset(db_session)
    repo = SQLAlchemyFundingRateRepository(db_session)
    ts = datetime(2026, 7, 9, 0, 0, tzinfo=timezone.utc)

    written = await repo.upsert_funding_rates([_rate(asset_id, ts, "0.0001")])

    assert written == 1
    stored = (
        await db_session.execute(
            text(
                "SELECT funding_rate FROM market_data.funding_rates "
                "WHERE asset_id = :a AND funding_time = :t"
            ),
            {"a": asset_id, "t": ts},
        )
    ).scalar_one()
    assert stored == Decimal("0.0001000000")  # NUMERIC(18,10)


async def test_funding_upsert_is_idempotent_and_revises(db_session: AsyncSession) -> None:
    asset_id = await _make_perp_asset(db_session)
    repo = SQLAlchemyFundingRateRepository(db_session)
    ts = datetime(2026, 7, 9, 0, 0, tzinfo=timezone.utc)

    await repo.upsert_funding_rates([_rate(asset_id, ts, "0.0001")])
    # same natural key, revised value — must update in place, not duplicate
    await repo.upsert_funding_rates([_rate(asset_id, ts, "0.0002")])

    count = (
        await db_session.execute(
            text("SELECT COUNT(*) FROM market_data.funding_rates WHERE asset_id = :a"),
            {"a": asset_id},
        )
    ).scalar_one()
    assert count == 1
    value = (
        await db_session.execute(
            text("SELECT funding_rate FROM market_data.funding_rates WHERE asset_id = :a"),
            {"a": asset_id},
        )
    ).scalar_one()
    assert value == Decimal("0.0002000000")


async def test_get_funding_rates_returns_oldest_to_newest(db_session: AsyncSession) -> None:
    asset_id = await _make_perp_asset(db_session)
    repo = SQLAlchemyFundingRateRepository(db_session)
    base = datetime(2026, 7, 9, 0, 0, tzinfo=timezone.utc)
    # insert out of order
    await repo.upsert_funding_rates([
        _rate(asset_id, base + timedelta(hours=16), "0.0003"),
        _rate(asset_id, base, "0.0001"),
        _rate(asset_id, base + timedelta(hours=8), "0.0002"),
    ])

    rates = await repo.get_funding_rates(asset_id, limit=100)

    assert [r.funding_rate for r in rates] == [
        Decimal("0.0001000000"),
        Decimal("0.0002000000"),
        Decimal("0.0003000000"),
    ]


async def test_get_latest_ts_watermark(db_session: AsyncSession) -> None:
    asset_id = await _make_perp_asset(db_session)
    repo = SQLAlchemyFundingRateRepository(db_session)
    assert await repo.get_latest_ts(asset_id) is None  # nothing yet

    base = datetime(2026, 7, 9, 0, 0, tzinfo=timezone.utc)
    latest = base + timedelta(hours=8)
    await repo.upsert_funding_rates([_rate(asset_id, base, "0.0001"), _rate(asset_id, latest, "0.0002")])

    assert await repo.get_latest_ts(asset_id) == latest

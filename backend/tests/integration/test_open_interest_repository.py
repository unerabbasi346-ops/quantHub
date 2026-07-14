# Governing specification: Doc 11 §2 (Idempotent ingestion); Doc 14 §10.9.5
#   (Financing Costs anchor, shared with funding rates)
#                          Doc 09 — migration b4f8e21ac9d3 (market_data.open_interest)
#                          handbook/KNOWN_LIMITATIONS.md S-10
# Per Doc 00 §14.11
#
# Exercises SQLAlchemyOpenInterestRepository against a live Postgres with
# migration b4f8e21ac9d3 applied — mirrors test_funding_rate_repository.py's
# exact shape (upsert idempotency, chronological read ordering, latest-ts
# watermark), the same repository-testing convention already established
# for the identical funding_rates pattern (real DB, not a mock — this
# codebase's repositories are integration-tested against Postgres, never
# behind a mocking framework).
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from quant_hub.domain.market_data.entities import AssetRef, OpenInterest
from quant_hub.persistence.repositories.market_data import (
    SQLAlchemyAssetRepository,
    SQLAlchemyOpenInterestRepository,
)


def _unique_symbol(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


async def _make_perp_asset(db_session: AsyncSession) -> uuid.UUID:
    return await SQLAlchemyAssetRepository(db_session).upsert(
        AssetRef(
            symbol=_unique_symbol("PERP"),
            exchange="TESTX",
            asset_class="crypto",
            instrument_type="PERPETUAL",
        )
    )


def _oi(asset_id: uuid.UUID, ts: datetime, usdt: str, contracts: str | None = None) -> OpenInterest:
    return OpenInterest(
        asset_id=asset_id,
        ts=ts,
        open_interest_usdt=Decimal(usdt),
        open_interest_contracts=Decimal(contracts) if contracts is not None else None,
        source="TESTX",
    )


async def test_open_interest_upsert_fresh_insert(db_session: AsyncSession) -> None:
    asset_id = await _make_perp_asset(db_session)
    repo = SQLAlchemyOpenInterestRepository(db_session)
    ts = datetime(2026, 7, 14, 0, 0, tzinfo=timezone.utc)

    written = await repo.upsert_open_interest([_oi(asset_id, ts, "6666884964.56092", "106325.509")])

    assert written == 1
    stored = (
        await db_session.execute(
            text(
                "SELECT open_interest_usdt, open_interest_contracts FROM market_data.open_interest "
                "WHERE asset_id = :a AND ts = :t"
            ),
            {"a": asset_id, "t": ts},
        )
    ).one()
    assert stored[0] == Decimal("6666884964.56092000")  # NUMERIC(28,8)
    assert stored[1] == Decimal("106325.50900000")


async def test_open_interest_contracts_nullable(db_session: AsyncSession) -> None:
    asset_id = await _make_perp_asset(db_session)
    repo = SQLAlchemyOpenInterestRepository(db_session)
    ts = datetime(2026, 7, 14, 0, 0, tzinfo=timezone.utc)

    await repo.upsert_open_interest([_oi(asset_id, ts, "1000")])

    stored = (
        await db_session.execute(
            text("SELECT open_interest_contracts FROM market_data.open_interest WHERE asset_id = :a"),
            {"a": asset_id},
        )
    ).scalar_one()
    assert stored is None


async def test_open_interest_upsert_is_idempotent_and_revises(db_session: AsyncSession) -> None:
    asset_id = await _make_perp_asset(db_session)
    repo = SQLAlchemyOpenInterestRepository(db_session)
    ts = datetime(2026, 7, 14, 0, 0, tzinfo=timezone.utc)

    await repo.upsert_open_interest([_oi(asset_id, ts, "1000")])
    # same (asset_id, ts) primary key, revised value — must update in place, not duplicate
    await repo.upsert_open_interest([_oi(asset_id, ts, "2000")])

    count = (
        await db_session.execute(
            text("SELECT COUNT(*) FROM market_data.open_interest WHERE asset_id = :a"),
            {"a": asset_id},
        )
    ).scalar_one()
    assert count == 1
    value = (
        await db_session.execute(
            text("SELECT open_interest_usdt FROM market_data.open_interest WHERE asset_id = :a"),
            {"a": asset_id},
        )
    ).scalar_one()
    assert value == Decimal("2000.00000000")


async def test_get_open_interest_history_returns_oldest_to_newest(db_session: AsyncSession) -> None:
    asset_id = await _make_perp_asset(db_session)
    repo = SQLAlchemyOpenInterestRepository(db_session)
    base = datetime(2026, 7, 14, 0, 0, tzinfo=timezone.utc)
    # insert out of order
    await repo.upsert_open_interest([
        _oi(asset_id, base + timedelta(hours=16), "3000"),
        _oi(asset_id, base, "1000"),
        _oi(asset_id, base + timedelta(hours=8), "2000"),
    ])

    rows = await repo.get_open_interest_history(asset_id, limit=100)

    assert [r.open_interest_usdt for r in rows] == [
        Decimal("1000.00000000"),
        Decimal("2000.00000000"),
        Decimal("3000.00000000"),
    ]


async def test_open_interest_get_latest_ts_watermark(db_session: AsyncSession) -> None:
    asset_id = await _make_perp_asset(db_session)
    repo = SQLAlchemyOpenInterestRepository(db_session)
    assert await repo.get_latest_ts(asset_id) is None  # nothing yet

    base = datetime(2026, 7, 14, 0, 0, tzinfo=timezone.utc)
    latest = base + timedelta(hours=8)
    await repo.upsert_open_interest([_oi(asset_id, base, "1000"), _oi(asset_id, latest, "2000")])

    assert await repo.get_latest_ts(asset_id) == latest

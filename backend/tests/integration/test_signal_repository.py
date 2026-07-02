# Governing specification: Doc 14 §10.6.4 — Signal Recording
#                          Doc 09 — Database Architecture (migration 7c7482e4e00a, Step 2.2)
# Per Doc 00 §14.11
#
# Exercises SQLAlchemySignalRepository against a live Postgres with
# migration 7c7482e4e00a applied. Mirrors test_corporate_actions_repository.py's
# structure.
#
# JUDGMENT CALL (flagged): StrategyRepository has no write method yet
# (Step 2.3 territory, not built — core.strategies row insertion here is
# raw SQL test fixture setup, the same pragmatic approach the existing
# repository tests use for their own foreign-key prerequisites (e.g.
# assets via SQLAlchemyAssetRepository.upsert, which DOES already exist).
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from quant_hub.domain.market_data.entities import AssetRef
from quant_hub.domain.strategy_engine.entities import Signal
from quant_hub.persistence.repositories.market_data import SQLAlchemyAssetRepository
from quant_hub.persistence.repositories.strategy_engine import SQLAlchemySignalRepository


def _unique_symbol(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


async def _make_strategy(db_session: AsyncSession) -> uuid.UUID:
    result = await db_session.execute(
        text(
            "INSERT INTO core.strategies (name, version) VALUES (:name, '1.0') RETURNING id"
        ),
        {"name": f"test-strategy-{uuid.uuid4().hex[:12]}"},
    )
    return result.scalar_one()


def _signal(asset: AssetRef, **overrides: object) -> Signal:
    defaults: dict[str, object] = dict(
        asset=asset, value=Decimal("0.42"), ts=datetime.now(timezone.utc)
    )
    defaults.update(overrides)
    return Signal(**defaults)  # type: ignore[arg-type]


async def test_record_persists_signal_and_returns_id(db_session: AsyncSession) -> None:
    assets = SQLAlchemyAssetRepository(db_session)
    signals = SQLAlchemySignalRepository(db_session)
    asset_ref = AssetRef(symbol=_unique_symbol("SIG"), exchange="test", asset_class="crypto")
    asset_id = await assets.upsert(asset_ref)
    strategy_id = await _make_strategy(db_session)

    signal_id = await signals.record(
        strategy_id, asset_id, _signal(asset_ref, metadata={"raw_alpha": "0.9"}), "VALID"
    )

    assert isinstance(signal_id, uuid.UUID)
    row = (
        await db_session.execute(
            text(
                "SELECT value, validation_status, metadata FROM core.signals WHERE id = :id"
            ),
            {"id": signal_id},
        )
    ).one()
    assert row.value == Decimal("0.42000000")
    assert row.validation_status == "VALID"
    assert row.metadata == {"raw_alpha": "0.9"}


async def test_record_is_append_only_no_upsert(db_session: AsyncSession) -> None:
    # Recording the "same" logical signal twice produces two rows, not one
    # revised row — P-5 immutability, no ON CONFLICT clause exists at all.
    assets = SQLAlchemyAssetRepository(db_session)
    signals = SQLAlchemySignalRepository(db_session)
    asset_ref = AssetRef(symbol=_unique_symbol("SIG"), exchange="test", asset_class="crypto")
    asset_id = await assets.upsert(asset_ref)
    strategy_id = await _make_strategy(db_session)
    ts = datetime.now(timezone.utc)

    await signals.record(strategy_id, asset_id, _signal(asset_ref, ts=ts), "VALID")
    await signals.record(strategy_id, asset_id, _signal(asset_ref, ts=ts), "VALID")

    count = (
        await db_session.execute(
            text(
                "SELECT COUNT(*) FROM core.signals "
                "WHERE strategy_id = :sid AND asset_id = :aid"
            ),
            {"sid": strategy_id, "aid": asset_id},
        )
    ).scalar_one()
    assert count == 2  # not deduplicated/revised — two distinct immutable events


async def test_get_latest_returns_most_recent_by_ts(db_session: AsyncSession) -> None:
    assets = SQLAlchemyAssetRepository(db_session)
    signals = SQLAlchemySignalRepository(db_session)
    asset_ref = AssetRef(symbol=_unique_symbol("SIG"), exchange="test", asset_class="crypto")
    asset_id = await assets.upsert(asset_ref)
    strategy_id = await _make_strategy(db_session)
    now = datetime.now(timezone.utc)

    await signals.record(
        strategy_id, asset_id, _signal(asset_ref, value=Decimal("-0.3"), ts=now - timedelta(minutes=10)), "VALID"
    )
    await signals.record(
        strategy_id, asset_id, _signal(asset_ref, value=Decimal("0.8"), ts=now), "VALID"
    )

    latest = await signals.get_latest(strategy_id, asset_id)

    assert latest is not None
    assert latest.value == Decimal("0.80000000")
    assert latest.strategy_id == strategy_id
    assert latest.asset_id == asset_id


async def test_get_latest_returns_none_when_no_signals_exist(db_session: AsyncSession) -> None:
    signals = SQLAlchemySignalRepository(db_session)
    result = await signals.get_latest(uuid.uuid4(), uuid.uuid4())
    assert result is None


async def test_invalid_signal_is_persisted_with_invalid_status(db_session: AsyncSession) -> None:
    # Doc 14 §10.6.4: every generated signal is recorded, including invalid
    # ones — verified here at the repository/schema level (no CHECK
    # constraint or trigger silently rejects an INVALID row).
    assets = SQLAlchemyAssetRepository(db_session)
    signals = SQLAlchemySignalRepository(db_session)
    asset_ref = AssetRef(symbol=_unique_symbol("SIG"), exchange="test", asset_class="crypto")
    asset_id = await assets.upsert(asset_ref)
    strategy_id = await _make_strategy(db_session)

    signal_id = await signals.record(strategy_id, asset_id, _signal(asset_ref), "INVALID")

    status = (
        await db_session.execute(
            text("SELECT validation_status FROM core.signals WHERE id = :id"),
            {"id": signal_id},
        )
    ).scalar_one()
    assert status == "INVALID"

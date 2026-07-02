# Governing specification: Doc 07 §Dependency Rules — Step 2.4
# Per Doc 00 §14.11
#
# Exercises the three real repository methods implemented in Step 2.4
# (AssetRepository.get_by_symbol_exchange, OHLCVRepository.get_bars,
# TickRepository.get_latest) against a live Postgres, and
# RepositoryBackedMarketDataView composed on top of the real repositories
# (not fakes) — the first real consumer proving these previously-stubbed
# methods work correctly end-to-end.
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from quant_hub.domain.market_data.entities import AssetRef, OHLCVBar, Tick
from quant_hub.infrastructure.strategy_engine.market_data_view import (
    RepositoryBackedMarketDataView,
)
from quant_hub.persistence.repositories.market_data import (
    SQLAlchemyAssetRepository,
    SQLAlchemyOHLCVRepository,
    SQLAlchemyTickRepository,
)


def _unique_symbol(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


async def test_get_by_symbol_exchange_resolves_existing_asset(db_session: AsyncSession) -> None:
    assets = SQLAlchemyAssetRepository(db_session)
    ref = AssetRef(symbol=_unique_symbol("MDV"), exchange="test", asset_class="crypto")
    asset_id = await assets.upsert(ref)

    resolved = await assets.get_by_symbol_exchange(ref.symbol, ref.exchange)

    assert resolved == asset_id


async def test_get_by_symbol_exchange_returns_none_for_unknown(db_session: AsyncSession) -> None:
    assets = SQLAlchemyAssetRepository(db_session)
    assert await assets.get_by_symbol_exchange("NOPE", "nowhere") is None


async def test_get_bars_returns_oldest_to_newest(db_session: AsyncSession) -> None:
    assets = SQLAlchemyAssetRepository(db_session)
    bars_repo = SQLAlchemyOHLCVRepository(db_session)
    ref = AssetRef(symbol=_unique_symbol("MDV"), exchange="test", asset_class="crypto")
    asset_id = await assets.upsert(ref)
    now = datetime.now(timezone.utc)

    to_insert = [
        OHLCVBar(
            asset_id=asset_id, interval="1h", ts=now - timedelta(hours=3 - i),
            open=Decimal("100"), high=Decimal("101"), low=Decimal("99"),
            close=Decimal(str(100 + i)), volume=Decimal("1"),
        )
        for i in range(3)
    ]
    await bars_repo.upsert_bars(to_insert)

    result = await bars_repo.get_bars(asset_id, "1h", limit=10)

    assert [b.close for b in result] == [Decimal("100.00000000"), Decimal("101.00000000"), Decimal("102.00000000")]
    assert result[0].ts < result[-1].ts  # oldest -> newest


async def test_get_bars_respects_limit(db_session: AsyncSession) -> None:
    assets = SQLAlchemyAssetRepository(db_session)
    bars_repo = SQLAlchemyOHLCVRepository(db_session)
    ref = AssetRef(symbol=_unique_symbol("MDV"), exchange="test", asset_class="crypto")
    asset_id = await assets.upsert(ref)
    now = datetime.now(timezone.utc)

    to_insert = [
        OHLCVBar(
            asset_id=asset_id, interval="1h", ts=now - timedelta(hours=5 - i),
            open=Decimal("100"), high=Decimal("101"), low=Decimal("99"),
            close=Decimal(str(100 + i)), volume=Decimal("1"),
        )
        for i in range(5)
    ]
    await bars_repo.upsert_bars(to_insert)

    result = await bars_repo.get_bars(asset_id, "1h", limit=2)

    assert len(result) == 2
    assert [b.close for b in result] == [Decimal("103.00000000"), Decimal("104.00000000")]  # most recent 2


async def test_tick_get_latest_returns_most_recent(db_session: AsyncSession) -> None:
    assets = SQLAlchemyAssetRepository(db_session)
    ticks_repo = SQLAlchemyTickRepository(db_session)
    ref = AssetRef(symbol=_unique_symbol("MDV"), exchange="test", asset_class="crypto")
    asset_id = await assets.upsert(ref)
    now = datetime.now(timezone.utc)

    await ticks_repo.save_tick(
        Tick(asset_id=asset_id, ts=now - timedelta(seconds=10), received_at=now, feed_origin="test", last=Decimal("1"))
    )
    await ticks_repo.save_tick(
        Tick(asset_id=asset_id, ts=now, received_at=now, feed_origin="test", last=Decimal("2"))
    )

    latest = await ticks_repo.get_latest(asset_id)

    assert latest is not None
    assert latest.last == Decimal("2.00000000")


async def test_view_reads_real_data_through_composed_repositories(db_session: AsyncSession) -> None:
    assets = SQLAlchemyAssetRepository(db_session)
    bars_repo = SQLAlchemyOHLCVRepository(db_session)
    ticks_repo = SQLAlchemyTickRepository(db_session)
    ref = AssetRef(symbol=_unique_symbol("MDV"), exchange="test", asset_class="crypto")
    asset_id = await assets.upsert(ref)
    now = datetime.now(timezone.utc)
    await bars_repo.upsert_bars([
        OHLCVBar(
            asset_id=asset_id, interval="1h", ts=now, open=Decimal("100"), high=Decimal("101"),
            low=Decimal("99"), close=Decimal("100.5"), volume=Decimal("1"),
        )
    ])

    view = RepositoryBackedMarketDataView(assets, bars_repo, ticks_repo)
    bars = await view.latest_bars(ref, "1h", limit=10)
    tick = await view.latest_tick(ref)

    assert len(bars) == 1
    assert bars[0].close == Decimal("100.50000000")
    assert tick is None  # none saved for this asset

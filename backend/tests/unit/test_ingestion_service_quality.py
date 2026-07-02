# Governing specification: Doc 11 §6 — Data Quality Scoring (wiring)
# Per Doc 00 §14.11
#
# Proves MarketDataIngestionService actually computes data_quality via
# domain/market_data/quality.py before persistence — not just that the
# quality functions work in isolation (see test_quality.py).
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from quant_hub.application.market_data.service import MarketDataIngestionService
from quant_hub.domain.market_data.entities import AssetRef, OHLCVBar, RawOHLCVBar, RawTick, Tick

_ASSET = AssetRef(symbol="BTC/USDT", exchange="binance", asset_class="crypto")
_ASSET_ID = uuid.uuid4()


class _FakeConnector:
    source_id = "binance"

    def __init__(self, bars=None, tick=None) -> None:
        self._bars = bars or []
        self._tick = tick

    async def fetch_ohlcv(self, symbol, interval, since=None, limit=500):
        return self._bars

    async def fetch_latest_tick(self, symbol):
        return self._tick


class _FakeAssetRepository:
    async def get_by_id(self, asset_id):
        return None

    async def get_by_symbol_exchange(self, symbol, exchange):
        return None

    async def list_active(self):
        return []

    async def upsert(self, asset: AssetRef):
        return _ASSET_ID


class _FakeOHLCVRepository:
    def __init__(self) -> None:
        self.persisted_bars: list[OHLCVBar] = []

    async def get_bars(self, asset_id, interval, limit=100):
        return []

    async def upsert_bars(self, bars: list[OHLCVBar]) -> int:
        self.persisted_bars.extend(bars)
        return len(bars)

    async def get_latest_ts(self, asset_id, interval):
        return None


class _FakeTickRepository:
    def __init__(self) -> None:
        self.saved_ticks: list[Tick] = []

    async def get_latest(self, asset_id):
        return None

    async def save_tick(self, tick: Tick) -> None:
        self.saved_ticks.append(tick)

    async def get_latest_ts(self, asset_id):
        return None


def _bar(**overrides: object) -> RawOHLCVBar:
    defaults: dict[object, object] = dict(
        asset=_ASSET,
        interval="1h",
        ts=datetime.now(timezone.utc) - timedelta(hours=1),
        open=Decimal("100"),
        high=Decimal("110"),
        low=Decimal("95"),
        close=Decimal("105"),
        volume=Decimal("10.5"),
        source="binance",
    )
    defaults.update(overrides)
    return RawOHLCVBar(**defaults)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_persisted_bar_gets_computed_clean_quality() -> None:
    connector = _FakeConnector(bars=[_bar()])
    assets, ohlcv, ticks = _FakeAssetRepository(), _FakeOHLCVRepository(), _FakeTickRepository()
    service = MarketDataIngestionService(connector, assets, ohlcv, ticks)

    await service.ingest_ohlcv("BTC/USDT", "1h")

    assert len(ohlcv.persisted_bars) == 1
    assert ohlcv.persisted_bars[0].data_quality == "CLEAN"


@pytest.mark.asyncio
async def test_fresh_tick_persisted_as_clean() -> None:
    now = datetime.now(timezone.utc)
    fresh_tick = RawTick(
        asset=_ASSET, ts=now, received_at=now, feed_origin="binance", last=Decimal("100")
    )
    connector = _FakeConnector(tick=fresh_tick)
    assets, ohlcv, ticks = _FakeAssetRepository(), _FakeOHLCVRepository(), _FakeTickRepository()
    service = MarketDataIngestionService(connector, assets, ohlcv, ticks)

    await service.ingest_latest_tick("BTC/USDT")

    assert len(ticks.saved_ticks) == 1
    assert ticks.saved_ticks[0].data_quality == "CLEAN"


@pytest.mark.asyncio
async def test_stale_tick_persisted_as_stale() -> None:
    received_at = datetime.now(timezone.utc)
    old_ts = received_at - timedelta(minutes=30)
    stale_tick = RawTick(
        asset=_ASSET,
        ts=old_ts,
        received_at=received_at,
        feed_origin="binance",
        last=Decimal("100"),
    )
    connector = _FakeConnector(tick=stale_tick)
    assets, ohlcv, ticks = _FakeAssetRepository(), _FakeOHLCVRepository(), _FakeTickRepository()
    service = MarketDataIngestionService(connector, assets, ohlcv, ticks)

    await service.ingest_latest_tick("BTC/USDT")

    assert len(ticks.saved_ticks) == 1
    assert ticks.saved_ticks[0].data_quality == "STALE"


@pytest.mark.asyncio
async def test_estimated_tick_provenance_flag_survives_quality_stage() -> None:
    received_at = datetime.now(timezone.utc)
    estimated_tick = RawTick(
        asset=_ASSET,
        ts=received_at,
        received_at=received_at,
        feed_origin="yfinance",
        last=Decimal("100"),
        data_quality="ESTIMATED",
    )
    connector = _FakeConnector(tick=estimated_tick)
    assets, ohlcv, ticks = _FakeAssetRepository(), _FakeOHLCVRepository(), _FakeTickRepository()
    service = MarketDataIngestionService(connector, assets, ohlcv, ticks)

    await service.ingest_latest_tick("BTC/USDT")

    assert ticks.saved_ticks[0].data_quality == "ESTIMATED"

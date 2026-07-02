# Governing specification: Doc 11 §7 — Incremental Updates (Data Engineering)
# Per Doc 00 §14.11
#
# Proves MarketDataIngestionService's late-arrival detection (Step 1.9)
# actually fires through the real service, not just in isolation.
from __future__ import annotations

import logging
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
    def __init__(self, watermark: datetime | None) -> None:
        self._watermark = watermark
        self.persisted_bars: list[OHLCVBar] = []

    async def get_bars(self, asset_id, interval, limit=100):
        return []

    async def upsert_bars(self, bars: list[OHLCVBar]) -> int:
        self.persisted_bars.extend(bars)
        return len(bars)

    async def get_latest_ts(self, asset_id, interval):
        return self._watermark


class _FakeTickRepository:
    def __init__(self, watermark: datetime | None) -> None:
        self._watermark = watermark
        self.saved_ticks: list[Tick] = []

    async def get_latest(self, asset_id):
        return None

    async def save_tick(self, tick: Tick) -> None:
        self.saved_ticks.append(tick)

    async def get_latest_ts(self, asset_id):
        return self._watermark


def _bar(ts: datetime) -> RawOHLCVBar:
    return RawOHLCVBar(
        asset=_ASSET,
        interval="1h",
        ts=ts,
        open=Decimal("100"),
        high=Decimal("110"),
        low=Decimal("95"),
        close=Decimal("105"),
        volume=Decimal("10.5"),
        source="binance",
    )


@pytest.mark.asyncio
async def test_bar_before_watermark_counted_and_logged_as_late(caplog) -> None:
    watermark = datetime(2026, 1, 2, tzinfo=timezone.utc)
    late_bar = _bar(datetime(2026, 1, 1, tzinfo=timezone.utc))  # before watermark
    on_time_bar = _bar(datetime(2026, 1, 3, tzinfo=timezone.utc))  # after watermark
    connector = _FakeConnector(bars=[late_bar, on_time_bar])
    assets = _FakeAssetRepository()
    ohlcv = _FakeOHLCVRepository(watermark=watermark)
    ticks = _FakeTickRepository(watermark=None)
    service = MarketDataIngestionService(connector, assets, ohlcv, ticks)

    with caplog.at_level(logging.INFO):
        result = await service.ingest_ohlcv("BTC/USDT", "1h")

    assert result.late_arrivals == 1
    assert result.persisted == 2  # both still persisted — late is a trace, not a rejection
    info_logs = [r for r in caplog.records if r.levelname == "INFO"]
    assert any("late-arriving" in r.getMessage() for r in info_logs)


@pytest.mark.asyncio
async def test_no_watermark_yet_nothing_is_late(caplog) -> None:
    # First-ever ingestion for this asset — no prior watermark, so nothing
    # can be "late" (this is what makes backfills of very old data not
    # spuriously flagged on a brand-new asset).
    connector = _FakeConnector(bars=[_bar(datetime(2020, 1, 1, tzinfo=timezone.utc))])
    assets = _FakeAssetRepository()
    ohlcv = _FakeOHLCVRepository(watermark=None)
    ticks = _FakeTickRepository(watermark=None)
    service = MarketDataIngestionService(connector, assets, ohlcv, ticks)

    with caplog.at_level(logging.INFO):
        result = await service.ingest_ohlcv("BTC/USDT", "1h")

    assert result.late_arrivals == 0
    assert not any("late-arriving" in r.getMessage() for r in caplog.records)


@pytest.mark.asyncio
async def test_late_arrival_logged_at_info_not_warning_or_error(caplog) -> None:
    watermark = datetime(2026, 1, 2, tzinfo=timezone.utc)
    late_bar = _bar(datetime(2026, 1, 1, tzinfo=timezone.utc))
    connector = _FakeConnector(bars=[late_bar])
    assets = _FakeAssetRepository()
    ohlcv = _FakeOHLCVRepository(watermark=watermark)
    ticks = _FakeTickRepository(watermark=None)
    service = MarketDataIngestionService(connector, assets, ohlcv, ticks)

    with caplog.at_level(logging.DEBUG):
        await service.ingest_ohlcv("BTC/USDT", "1h")

    late_records = [r for r in caplog.records if "late-arriving" in r.getMessage()]
    assert len(late_records) == 1
    assert late_records[0].levelname == "INFO"  # neutral trace, not an anomaly signal


@pytest.mark.asyncio
async def test_late_tick_logged(caplog) -> None:
    watermark = datetime.now(timezone.utc)
    late_ts = watermark - timedelta(hours=1)
    tick = RawTick(
        asset=_ASSET, ts=late_ts, received_at=watermark, feed_origin="binance", last=Decimal("100")
    )
    connector = _FakeConnector(tick=tick)
    assets = _FakeAssetRepository()
    ohlcv = _FakeOHLCVRepository(watermark=None)
    ticks = _FakeTickRepository(watermark=watermark)
    service = MarketDataIngestionService(connector, assets, ohlcv, ticks)

    with caplog.at_level(logging.INFO):
        await service.ingest_latest_tick("BTC/USDT")

    assert len(ticks.saved_ticks) == 1  # still persisted
    assert any("late-arriving" in r.getMessage() for r in caplog.records)

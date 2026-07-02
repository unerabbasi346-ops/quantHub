# Governing specification: Doc 11 §2 — Historical Data Ingestion (Validate stage wiring)
#                          Doc 11 §5 — Data Validation Engine
# Per Doc 00 §14.11
#
# End-to-end proof (fakes, no DB/network needed) that
# MarketDataIngestionService actually rejects an invalid record before it
# reaches the repository layer — not just that validate_bar()/
# validate_tick() work in isolation (see test_validation.py).
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

    def __init__(self, bars: list[RawOHLCVBar] | None = None, tick: RawTick | None = None) -> None:
        self._bars = bars or []
        self._tick = tick

    async def fetch_ohlcv(self, symbol, interval, since=None, limit=500):
        return self._bars

    async def fetch_latest_tick(self, symbol):
        return self._tick


class _FakeAssetRepository:
    def __init__(self) -> None:
        self.upsert_calls: list[AssetRef] = []

    async def get_by_id(self, asset_id):
        return None

    async def get_by_symbol_exchange(self, symbol, exchange):
        return None

    async def list_active(self):
        return []

    async def upsert(self, asset: AssetRef):
        self.upsert_calls.append(asset)
        return _ASSET_ID


class _FakeOHLCVRepository:
    def __init__(self) -> None:
        self.persisted_bars: list[OHLCVBar] = []

    async def get_bars(self, asset_id, interval, limit=100):
        return []

    async def upsert_bars(self, bars: list[OHLCVBar]) -> int:
        self.persisted_bars.extend(bars)
        return len(bars)


class _FakeTickRepository:
    def __init__(self) -> None:
        self.saved_ticks: list[Tick] = []

    async def get_latest(self, asset_id):
        return None

    async def save_tick(self, tick: Tick) -> None:
        self.saved_ticks.append(tick)


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
async def test_invalid_bar_is_rejected_not_persisted_and_logged(caplog) -> None:
    valid_bar = _bar()
    invalid_bar = _bar(open=Decimal("-999"), close=Decimal("-999"))  # negative price
    connector = _FakeConnector(bars=[valid_bar, invalid_bar])
    assets, ohlcv, ticks = _FakeAssetRepository(), _FakeOHLCVRepository(), _FakeTickRepository()
    service = MarketDataIngestionService(connector, assets, ohlcv, ticks)

    with caplog.at_level(logging.WARNING):
        result = await service.ingest_ohlcv("BTC/USDT", "1h")

    # Only the valid bar reached the repository.
    assert len(ohlcv.persisted_bars) == 1
    assert ohlcv.persisted_bars[0].open == Decimal("100")

    # Accounting is honest: fetched counts both, persisted/rejected split correctly.
    assert result.fetched == 2
    assert result.persisted == 1
    assert result.rejected == 1

    # Not a silent drop: a warning trace exists naming the failure.
    warnings = [r for r in caplog.records if r.levelname == "WARNING"]
    assert len(warnings) == 1
    message = warnings[0].getMessage()
    assert "rejected invalid bar" in message
    assert "-999" in message


@pytest.mark.asyncio
async def test_all_bars_invalid_skips_asset_upsert_entirely() -> None:
    invalid_bar = _bar(volume=Decimal("-1"))
    connector = _FakeConnector(bars=[invalid_bar])
    assets, ohlcv, ticks = _FakeAssetRepository(), _FakeOHLCVRepository(), _FakeTickRepository()
    service = MarketDataIngestionService(connector, assets, ohlcv, ticks)

    result = await service.ingest_ohlcv("BTC/USDT", "1h")

    assert result == type(result)(fetched=1, persisted=0, rejected=1)
    assert ohlcv.persisted_bars == []
    assert assets.upsert_calls == []  # no wasted DB write for a fully-rejected batch


@pytest.mark.asyncio
async def test_invalid_tick_is_rejected_not_persisted_and_logged(caplog) -> None:
    invalid_tick = RawTick(
        asset=_ASSET,
        ts=datetime.now(timezone.utc),
        received_at=datetime.now(timezone.utc),
        feed_origin="binance",
        last=None,
        bid=None,
        ask=None,  # all three prices missing
    )
    connector = _FakeConnector(tick=invalid_tick)
    assets, ohlcv, ticks = _FakeAssetRepository(), _FakeOHLCVRepository(), _FakeTickRepository()
    service = MarketDataIngestionService(connector, assets, ohlcv, ticks)

    with caplog.at_level(logging.WARNING):
        await service.ingest_latest_tick("BTC/USDT")

    assert ticks.saved_ticks == []
    assert assets.upsert_calls == []
    warnings = [r for r in caplog.records if r.levelname == "WARNING"]
    assert len(warnings) == 1
    assert "rejected invalid tick" in warnings[0].getMessage()


@pytest.mark.asyncio
async def test_valid_tick_is_persisted() -> None:
    valid_tick = RawTick(
        asset=_ASSET,
        ts=datetime.now(timezone.utc),
        received_at=datetime.now(timezone.utc),
        feed_origin="binance",
        last=Decimal("100"),
    )
    connector = _FakeConnector(tick=valid_tick)
    assets, ohlcv, ticks = _FakeAssetRepository(), _FakeOHLCVRepository(), _FakeTickRepository()
    service = MarketDataIngestionService(connector, assets, ohlcv, ticks)

    await service.ingest_latest_tick("BTC/USDT")

    assert len(ticks.saved_ticks) == 1
    assert ticks.saved_ticks[0].last == Decimal("100")

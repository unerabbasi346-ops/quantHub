# Governing specification: Doc 14 §10.6.4; P-1
# Per Doc 00 §14.11
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from quant_hub.application.strategy_engine.reference_strategies.moving_average_crossover import (
    MovingAverageCrossoverStrategy,
)
from quant_hub.domain.market_data.entities import AssetRef, OHLCVBar
from quant_hub.domain.strategy_engine.strategy import MarketDataView

_ASSET = AssetRef(symbol="BTC/USDT", exchange="binance", asset_class="crypto")


def _bar(close: str, ts: datetime) -> OHLCVBar:
    return OHLCVBar(
        asset_id=__import__("uuid").uuid4(),
        interval="1h",
        ts=ts,
        open=Decimal(close),
        high=Decimal(close),
        low=Decimal(close),
        close=Decimal(close),
        volume=Decimal("1"),
    )


class _FixedView(MarketDataView):
    def __init__(self, bars: list[OHLCVBar]) -> None:
        self._bars = bars

    async def latest_bars(self, asset, interval, limit=100):
        return self._bars[-limit:]

    async def latest_tick(self, asset):
        return None


def _config(**overrides: object) -> dict:
    defaults = {"symbol": "BTC/USDT", "exchange": "binance", "short_window": 3, "long_window": 6}
    defaults.update(overrides)
    return defaults


@pytest.mark.asyncio
async def test_insufficient_history_returns_no_signal() -> None:
    now = datetime.now(timezone.utc)
    bars = [_bar("100", now - timedelta(hours=i)) for i in range(3)]  # fewer than long_window=6
    strategy = MovingAverageCrossoverStrategy()

    signals = await strategy.generate_signals(_FixedView(bars), _config())

    assert signals == []


@pytest.mark.asyncio
async def test_uptrend_produces_positive_conviction() -> None:
    now = datetime.now(timezone.utc)
    # Oldest -> newest, rising closes: short MA (last 3) > long MA (all 6).
    closes = ["100", "101", "102", "103", "104", "110"]
    bars = [_bar(c, now - timedelta(hours=len(closes) - i)) for i, c in enumerate(closes)]
    strategy = MovingAverageCrossoverStrategy()

    signals = await strategy.generate_signals(_FixedView(bars), _config())

    assert len(signals) == 1
    assert signals[0].value > 0
    assert signals[0].asset == _ASSET
    assert signals[0].ts == bars[-1].ts


@pytest.mark.asyncio
async def test_downtrend_produces_negative_conviction() -> None:
    now = datetime.now(timezone.utc)
    closes = ["110", "104", "103", "102", "101", "90"]
    bars = [_bar(c, now - timedelta(hours=len(closes) - i)) for i, c in enumerate(closes)]
    strategy = MovingAverageCrossoverStrategy()

    signals = await strategy.generate_signals(_FixedView(bars), _config())

    assert len(signals) == 1
    assert signals[0].value < 0


@pytest.mark.asyncio
async def test_value_is_clamped_to_validation_range() -> None:
    now = datetime.now(timezone.utc)
    # Extreme divergence: short MA wildly above long MA.
    closes = ["1", "1", "1", "1", "1", "100000"]
    bars = [_bar(c, now - timedelta(hours=len(closes) - i)) for i, c in enumerate(closes)]
    strategy = MovingAverageCrossoverStrategy()

    signals = await strategy.generate_signals(_FixedView(bars), _config())

    assert len(signals) == 1
    assert Decimal("-1") <= signals[0].value <= Decimal("1")


@pytest.mark.asyncio
async def test_config_defaults_apply_when_omitted() -> None:
    now = datetime.now(timezone.utc)
    bars = [_bar("100", now - timedelta(hours=i)) for i in range(25)]
    strategy = MovingAverageCrossoverStrategy()

    # Only symbol/exchange supplied — short_window/long_window/interval default.
    signals = await strategy.generate_signals(
        _FixedView(bars), {"symbol": "BTC/USDT", "exchange": "binance"}
    )

    assert isinstance(signals, list)  # does not raise on missing optional keys

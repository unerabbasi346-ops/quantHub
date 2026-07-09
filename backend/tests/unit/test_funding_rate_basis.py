# Governing specification: Doc 14 §10.6.4; P-1; handbook S-10 (perpetuals)
# Per Doc 00 §14.11
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from quant_hub.application.strategy_engine.reference_strategies.funding_rate_basis import (
    FundingRateBasisStrategy,
)
from quant_hub.domain.market_data.entities import AssetRef, FundingRate
from quant_hub.domain.strategy_engine.strategy import MarketDataView

_NOW = datetime(2026, 7, 9, 0, 0, tzinfo=timezone.utc)


def _fr(rate: str, hours: int) -> FundingRate:
    return FundingRate(
        asset_id=__import__("uuid").uuid4(),
        funding_time=_NOW + timedelta(hours=hours),
        funding_rate=Decimal(rate),
        source="binance",
    )


class _FundingView(MarketDataView):
    def __init__(self, rates: list[FundingRate]) -> None:
        self._rates = rates

    async def latest_bars(self, asset, interval, limit=100):  # pragma: no cover
        return []

    async def latest_tick(self, asset):  # pragma: no cover
        return None

    async def latest_funding_rates(self, asset, limit=100):
        return self._rates[-limit:]


def _config(**overrides: object) -> dict:
    defaults = {"symbol": "BTC/USDT:USDT", "exchange": "binance"}
    defaults.update(overrides)
    return defaults


@pytest.mark.asyncio
async def test_no_funding_data_returns_no_signal() -> None:
    signals = await FundingRateBasisStrategy().generate_signals(_FundingView([]), _config())
    assert signals == []


@pytest.mark.asyncio
async def test_positive_funding_leans_short_negative_value() -> None:
    # positive funding -> longs pay shorts -> collect by going short -> value < 0
    rates = [_fr("0.0001", 0), _fr("0.0002", 8), _fr("0.00015", 16)]
    signals = await FundingRateBasisStrategy().generate_signals(_FundingView(rates), _config())
    assert len(signals) == 1
    assert signals[0].value < 0
    assert signals[0].asset.instrument_type == "PERPETUAL"
    assert signals[0].ts == rates[-1].funding_time


@pytest.mark.asyncio
async def test_negative_funding_leans_long_positive_value() -> None:
    rates = [_fr("-0.0001", 0), _fr("-0.0002", 8)]
    signals = await FundingRateBasisStrategy().generate_signals(_FundingView(rates), _config())
    assert len(signals) == 1
    assert signals[0].value > 0


@pytest.mark.asyncio
async def test_value_clamped_to_validation_range() -> None:
    # a huge funding rate * scale would exceed 1 -> clamped
    rates = [_fr("0.5", 0)]
    signals = await FundingRateBasisStrategy().generate_signals(_FundingView(rates), _config())
    assert len(signals) == 1
    assert signals[0].value == Decimal("-1")  # clamped floor (positive funding -> short)


@pytest.mark.asyncio
async def test_scale_and_window_config_applied() -> None:
    rates = [_fr("0.0001", 0), _fr("0.0003", 8)]
    # scale 5000, mean of both = 0.0002 -> -0.0002*5000 = -1.0 (clamped exactly)
    signals = await FundingRateBasisStrategy().generate_signals(
        _FundingView(rates), _config(scale="5000", window=2)
    )
    assert signals[0].value == Decimal("-1")
    assert signals[0].metadata["window"] == "2"

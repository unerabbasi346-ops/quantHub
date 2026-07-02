# Governing specification: Doc 02 §Dependency Rules; Doc 07 §Layers
# Per Doc 00 §14.11
#
# No database needed — fakes for AssetRepository/OHLCVRepository/TickRepository.
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from quant_hub.domain.market_data.entities import AssetRef, OHLCVBar, Tick
from quant_hub.infrastructure.strategy_engine.market_data_view import (
    RepositoryBackedMarketDataView,
)

_ASSET = AssetRef(symbol="BTC/USDT", exchange="binance", asset_class="crypto")
_ASSET_ID = uuid.uuid4()


class _FakeAssets:
    def __init__(self, known: dict[tuple[str, str], uuid.UUID] | None = None) -> None:
        self._known = known or {}

    async def get_by_symbol_exchange(self, symbol, exchange):
        return self._known.get((symbol, exchange))


class _FakeBars:
    def __init__(self, bars: list[OHLCVBar] | None = None) -> None:
        self._bars = bars or []

    async def get_bars(self, asset_id, interval, limit=100):
        assert asset_id == _ASSET_ID
        return self._bars[-limit:]


class _FakeTicks:
    def __init__(self, tick: Tick | None = None) -> None:
        self._tick = tick

    async def get_latest(self, asset_id):
        assert asset_id == _ASSET_ID
        return self._tick


def _bar(**overrides: object) -> OHLCVBar:
    defaults: dict[str, object] = dict(
        asset_id=_ASSET_ID,
        interval="1h",
        ts=datetime.now(timezone.utc),
        open=Decimal("100"),
        high=Decimal("101"),
        low=Decimal("99"),
        close=Decimal("100.5"),
        volume=Decimal("10"),
    )
    defaults.update(overrides)
    return OHLCVBar(**defaults)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_latest_bars_resolves_asset_and_delegates() -> None:
    bars = [_bar(), _bar()]
    view = RepositoryBackedMarketDataView(
        assets=_FakeAssets({("BTC/USDT", "binance"): _ASSET_ID}),
        bars=_FakeBars(bars),
        ticks=_FakeTicks(),
    )

    result = await view.latest_bars(_ASSET, "1h", limit=10)

    assert result == bars


@pytest.mark.asyncio
async def test_latest_bars_returns_empty_for_unregistered_asset() -> None:
    view = RepositoryBackedMarketDataView(
        assets=_FakeAssets({}),  # nothing registered
        bars=_FakeBars([_bar()]),
        ticks=_FakeTicks(),
    )

    result = await view.latest_bars(_ASSET, "1h")

    assert result == []


@pytest.mark.asyncio
async def test_latest_tick_resolves_asset_and_delegates() -> None:
    tick = Tick(asset_id=_ASSET_ID, ts=datetime.now(timezone.utc), received_at=datetime.now(timezone.utc), feed_origin="binance", last=Decimal("100"))
    view = RepositoryBackedMarketDataView(
        assets=_FakeAssets({("BTC/USDT", "binance"): _ASSET_ID}),
        bars=_FakeBars(),
        ticks=_FakeTicks(tick),
    )

    result = await view.latest_tick(_ASSET)

    assert result == tick


@pytest.mark.asyncio
async def test_latest_tick_returns_none_for_unregistered_asset() -> None:
    view = RepositoryBackedMarketDataView(
        assets=_FakeAssets({}), bars=_FakeBars(), ticks=_FakeTicks(Tick(
            asset_id=_ASSET_ID, ts=datetime.now(timezone.utc), received_at=datetime.now(timezone.utc), feed_origin="binance"
        ))
    )

    result = await view.latest_tick(_ASSET)

    assert result is None

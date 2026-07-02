# Governing specification: application/strategy_engine/engine.py — Step 2.4
# Per Doc 00 §14.11
#
# Proves run_strategy_once wires resolve-strategy -> resolve-plugin ->
# generate_signals -> validate+record end-to-end with fakes (no DB).
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from quant_hub.application.strategy_engine.engine import run_strategy_once
from quant_hub.application.strategy_engine.signal_recording_service import (
    SignalRecordingService,
)
from quant_hub.domain.market_data.entities import AssetRef
from quant_hub.domain.strategy_engine.entities import Signal, StrategyRef
from quant_hub.domain.strategy_engine.strategy import MarketDataView, Strategy
from quant_hub.domain.strategy_engine.validation import VALIDATION_VALID
from quant_hub.infrastructure.strategy_engine.plugin_registry import register_plugin

_ASSET = AssetRef(symbol="ETH/USDT", exchange="binance", asset_class="crypto")
_ASSET_ID = uuid.uuid4()
_STRATEGY_ID = uuid.uuid4()


class _FakeStrategies:
    async def upsert(self, strategy_ref):
        return _STRATEGY_ID

    async def get_by_id(self, strategy_id):
        return None

    async def list_by_portfolio(self, portfolio_id):
        return []


class _FakeAssets:
    async def get_by_symbol_exchange(self, symbol, exchange):
        return _ASSET_ID if (symbol, exchange) == (_ASSET.symbol, _ASSET.exchange) else None

    async def upsert(self, asset):
        raise AssertionError("engine must not call assets.upsert() for a signal's asset")

    async def get_by_id(self, asset_id):
        return None

    async def list_active(self):
        return []


class _FakeSignals:
    def __init__(self) -> None:
        self.recorded: list[tuple] = []

    async def get_latest(self, strategy_id, asset_id):
        return None

    async def record(self, strategy_id, asset_id, signal, validation_status):
        self.recorded.append((strategy_id, asset_id, signal, validation_status))
        return uuid.uuid4()


class _NullView(MarketDataView):
    async def latest_bars(self, asset, interval, limit=100):
        return []

    async def latest_tick(self, asset):
        return None


class _EmitsOneSignal(Strategy):
    async def generate_signals(self, view, config):
        return [Signal(asset=_ASSET, value=Decimal("0.3"), ts=datetime.now(timezone.utc))]


class _EmitsNothing(Strategy):
    async def generate_signals(self, view, config):
        return []


register_plugin("test-engine-emits-one", _EmitsOneSignal)
register_plugin("test-engine-emits-nothing", _EmitsNothing)


@pytest.mark.asyncio
async def test_run_strategy_once_records_emitted_signal() -> None:
    signals_repo = _FakeSignals()
    strategy_ref = StrategyRef(name="test-engine-emits-one", version="1.0.0")

    recorded = await run_strategy_once(
        strategy_ref,
        strategies=_FakeStrategies(),
        assets=_FakeAssets(),
        view=_NullView(),
        recorder=SignalRecordingService(signals_repo),
    )

    assert len(recorded) == 1
    assert recorded[0].strategy_id == _STRATEGY_ID
    assert recorded[0].asset_id == _ASSET_ID
    assert recorded[0].validation_status == VALIDATION_VALID
    assert len(signals_repo.recorded) == 1


@pytest.mark.asyncio
async def test_run_strategy_once_handles_no_signals() -> None:
    signals_repo = _FakeSignals()
    strategy_ref = StrategyRef(name="test-engine-emits-nothing", version="1.0.0")

    recorded = await run_strategy_once(
        strategy_ref,
        strategies=_FakeStrategies(),
        assets=_FakeAssets(),
        view=_NullView(),
        recorder=SignalRecordingService(signals_repo),
    )

    assert recorded == []
    assert signals_repo.recorded == []


@pytest.mark.asyncio
async def test_run_strategy_once_raises_for_unregistered_asset() -> None:
    class _AssetsKnowsNothing:
        async def get_by_symbol_exchange(self, symbol, exchange):
            return None

    signals_repo = _FakeSignals()
    strategy_ref = StrategyRef(name="test-engine-emits-one", version="1.0.0")

    with pytest.raises(ValueError, match="unregistered asset"):
        await run_strategy_once(
            strategy_ref,
            strategies=_FakeStrategies(),
            assets=_AssetsKnowsNothing(),
            view=_NullView(),
            recorder=SignalRecordingService(signals_repo),
        )

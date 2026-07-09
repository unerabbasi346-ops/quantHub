# Governing specification: Doc 14 §10.3 — Backtesting Engine Architecture
#   §10.3.4 (point-in-time), §10.3.6 (deterministic replay); P-13
# Per Doc 00 §14.11
#
# Point-in-time view correctness + engine determinism, with fakes for the
# persistence collaborators. The real Step 3.1–3.5 pipeline reuse is proven
# end-to-end in the live verification; here the engine drives REAL Sizing /
# Construction (PositionSizingService / PortfolioConstructionService with the
# reference plugins) and fakes only order-gen / execution / persistence.
from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4, uuid7

import pytest

from quant_hub.application.backtesting.engine import BacktestEngine
from quant_hub.application.portfolio.reference_constructors.weighted_sum import WeightedSumConstructor
from quant_hub.application.portfolio.reference_sizers.linear_conviction import LinearConvictionSizer
from quant_hub.domain.backtesting.entities import BacktestConfig
from quant_hub.domain.execution.entities import (
    OrderSide,
    OrderStatus,
    OrderType,
    RecordedOrder,
    TimeInForce,
)
from quant_hub.domain.execution.entities import TargetPosition  # noqa: F401 (type context)
from quant_hub.domain.market_data.entities import AssetRef, FundingRate, OHLCVBar
from quant_hub.domain.strategy_engine.entities import RecordedSignal, Signal
from quant_hub.domain.strategy_engine.strategy import MarketDataView, Strategy
from quant_hub.infrastructure.backtesting.point_in_time_view import PointInTimeMarketDataView

_ASSET = AssetRef(symbol="BTC/USDT", exchange="binance", asset_class="crypto")
_T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _bar(i: int, close: str) -> OHLCVBar:
    return OHLCVBar(
        asset_id=uuid4(), interval="1h", ts=_T0 + timedelta(hours=i),
        open=Decimal(close), high=Decimal(close), low=Decimal(close), close=Decimal(close),
        volume=Decimal("1"), vwap=None, trade_count=None, adjustment_factor=None,
        data_quality=Decimal("1"), source="test",
    )


# ── PointInTimeMarketDataView (§10.3.4) ─────────────────────────────────────

@pytest.mark.asyncio
async def test_view_returns_trailing_limit_of_the_clamped_slice() -> None:
    bars = [_bar(i, str(100 + i)) for i in range(5)]  # closes 100..104
    view = PointInTimeMarketDataView(bars, _ASSET, "1h")
    got = await view.latest_bars(_ASSET, "1h", limit=3)
    assert [b.close for b in got] == [Decimal("102"), Decimal("103"), Decimal("104")]


@pytest.mark.asyncio
async def test_view_never_exposes_beyond_its_slice() -> None:
    # the engine constructs the view over bars[:i+1]; the view can only ever
    # return what it was given -> no future leakage (§10.3.4)
    bars = [_bar(i, str(100 + i)) for i in range(3)]
    view = PointInTimeMarketDataView(bars, _ASSET, "1h")
    got = await view.latest_bars(_ASSET, "1h", limit=100)
    assert len(got) == 3 and got[-1].close == Decimal("102")


@pytest.mark.asyncio
async def test_view_unknown_asset_or_interval_is_empty() -> None:
    view = PointInTimeMarketDataView([_bar(0, "100")], _ASSET, "1h")
    assert await view.latest_bars(AssetRef("ETH/USDT", "binance", "crypto"), "1h") == []
    assert await view.latest_bars(_ASSET, "1d") == []
    assert await view.latest_tick(_ASSET) is None


# ── PointInTimeMarketDataView funding (additive, §10.3.4) ───────────────────


def _funding(i: int, rate: str) -> FundingRate:
    return FundingRate(
        asset_id=uuid4(), funding_time=_T0 + timedelta(hours=8 * i),
        funding_rate=Decimal(rate),
    )


@pytest.mark.asyncio
async def test_view_no_funding_defaults_empty() -> None:
    # Backward compatibility: a view constructed without funding serves none.
    view = PointInTimeMarketDataView([_bar(0, "100")], _ASSET, "1h")
    assert await view.latest_funding_rates(_ASSET) == []


@pytest.mark.asyncio
async def test_view_funding_clamped_to_as_of() -> None:
    # Funding at t=0,8,16,24h; as_of at 16h -> only the first three are visible
    # (never a future observation), newest last, trailing `limit` honoured.
    funding = [_funding(i, f"0.000{i}") for i in range(4)]
    view = PointInTimeMarketDataView(
        [_bar(0, "100")], _ASSET, "1h", funding=funding, as_of=_T0 + timedelta(hours=16),
    )
    got = await view.latest_funding_rates(_ASSET, limit=100)
    assert [f.funding_time for f in got] == [_T0, _T0 + timedelta(hours=8), _T0 + timedelta(hours=16)]
    # trailing-limit semantics, same as bars
    assert [f.funding_time for f in await view.latest_funding_rates(_ASSET, limit=2)] == [
        _T0 + timedelta(hours=8), _T0 + timedelta(hours=16),
    ]


@pytest.mark.asyncio
async def test_view_funding_unknown_asset_is_empty() -> None:
    view = PointInTimeMarketDataView(
        [_bar(0, "100")], _ASSET, "1h", funding=[_funding(0, "0.0001")], as_of=_T0,
    )
    assert await view.latest_funding_rates(AssetRef("ETH/USDT", "binance", "crypto")) == []


# ── Engine determinism + orchestration (fakes for persistence) ──────────────


class _FakeStrategy(Strategy):
    """Emits a fixed positive conviction once >=2 bars of history exist."""

    async def generate_signals(
        self, view: MarketDataView, config: Mapping[str, object]
    ) -> Sequence[Signal]:
        bars = await view.latest_bars(_ASSET, "1h", limit=100)
        if len(bars) < 2:
            return []
        return [Signal(asset=_ASSET, value=Decimal("0.5"), ts=bars[-1].ts, metadata={})]


class _FakeBars:
    def __init__(self, bars: list[OHLCVBar]) -> None:
        self._bars = bars

    async def get_bars_range(self, asset_id, interval, start, end) -> list[OHLCVBar]:
        return list(self._bars)


class _FakeAssets:
    def __init__(self, asset_id: UUID) -> None:
        self._asset_id = asset_id

    async def get_by_symbol_exchange(self, symbol, exchange):
        return self._asset_id


class _FakePositions:
    """Flat throughout — isolates the engine loop from real position math."""

    async def get_by_portfolio_and_asset(self, portfolio_id, asset_id):
        return None


class _FakeSignalRecorder:
    async def record_signal(self, strategy_id, asset_id, signal) -> RecordedSignal:
        return RecordedSignal(
            id=uuid7(), strategy_id=strategy_id, asset_id=asset_id, value=signal.value,
            ts=signal.ts, validation_status="VALID", metadata={}, created_at=_T0,
        )


class _FakeOrderGen:
    async def generate_order(self, *, target, current, portfolio_id, strategy_id, signal_id) -> RecordedOrder:
        return RecordedOrder(
            id=uuid7(), idempotency_key=uuid7(), portfolio_id=portfolio_id, strategy_id=strategy_id,
            asset_id=uuid4(), side=OrderSide.BUY, quantity=Decimal("0.01"), order_type=OrderType.MARKET,
            time_in_force=TimeInForce.DAY, status=OrderStatus.CREATED, signal_id=signal_id, created_at=_T0,
        )


class _FakeExecutionOutcome:
    terminal_status = OrderStatus.FILLED


class _FakeExecution:
    def __init__(self) -> None:
        self.calls = 0

    async def process_order(self, order, request, executed_at) -> _FakeExecutionOutcome:
        self.calls += 1
        return _FakeExecutionOutcome()


class _FakeBacktests:
    def __init__(self) -> None:
        self.result = None

    async def create(self, config, strategy_id) -> UUID:
        return uuid7()

    async def complete(self, backtest_id, result) -> None:
        self.result = result


def _engine(bars: list[OHLCVBar], execution=None):
    return BacktestEngine(
        bars=_FakeBars(bars), assets=_FakeAssets(uuid4()), positions=_FakePositions(),
        backtests=_FakeBacktests(), signal_recorder=_FakeSignalRecorder(),
        sizer=LinearConvictionSizer(), constructor=WeightedSumConstructor(),
        order_gen=_FakeOrderGen(), execution=execution or _FakeExecution(),
        strategy_plugin=_FakeStrategy(),
    )


def _config() -> BacktestConfig:
    return BacktestConfig(
        name="det-test", symbol="BTC/USDT", exchange="binance", asset_class="crypto",
        interval="1h", strategy_config={}, start=_T0, end=_T0 + timedelta(hours=10),
        initial_capital=Decimal("100000"), max_position_pct=Decimal("0.10"),
    )


@pytest.mark.asyncio
async def test_engine_replays_all_bars_and_fills() -> None:
    bars = [_bar(i, str(100 + i)) for i in range(5)]
    execution = _FakeExecution()
    engine = _engine(bars, execution)
    _bt_id, result = await engine.run(_config(), strategy_id=uuid4(), portfolio_id=uuid4())
    assert result.bars_processed == 5
    # signals emitted from bar index 1 onward (>=2 bars) -> 4 signals/orders/fills
    assert result.signals_generated == 4
    assert result.orders_created == 4 and result.orders_filled == 4
    assert execution.calls == 4  # the engine delegated to the (real-typed) execution service


@pytest.mark.asyncio
async def test_identical_replay_reproduces_identical_hash() -> None:
    bars = [_bar(i, str(100 + i)) for i in range(6)]
    _id1, r1 = await _engine(list(bars)).run(_config(), strategy_id=uuid4(), portfolio_id=uuid4())
    _id2, r2 = await _engine(list(bars)).run(_config(), strategy_id=uuid4(), portfolio_id=uuid4())
    # different strategy_id/portfolio_id/UUIDs, SAME economic outputs -> same hash (§10.3.6)
    assert r1.reproducibility_hash == r2.reproducibility_hash
    assert r1.orders_filled == r2.orders_filled


@pytest.mark.asyncio
async def test_different_data_changes_hash() -> None:
    bars_a = [_bar(i, str(100 + i)) for i in range(6)]
    bars_b = [_bar(i, str(200 + i)) for i in range(6)]  # different prices
    _i, ra = await _engine(bars_a).run(_config(), strategy_id=uuid4(), portfolio_id=uuid4())
    _j, rb = await _engine(bars_b).run(_config(), strategy_id=uuid4(), portfolio_id=uuid4())
    assert ra.reproducibility_hash != rb.reproducibility_hash

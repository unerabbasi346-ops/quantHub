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
        self.exit_calls: list[dict] = []  # calls that carried Rule 4 trade-result kwargs

    async def process_order(
        self, order, request, executed_at,
        price_return_pct=None, market_move_pct=None, exit_reason=None,
    ) -> _FakeExecutionOutcome:
        self.calls += 1
        if exit_reason is not None:
            self.exit_calls.append({
                "price_return_pct": price_return_pct,
                "market_move_pct": market_move_pct,
                "exit_reason": exit_reason,
            })
        return _FakeExecutionOutcome()


class _FakeBacktests:
    def __init__(self) -> None:
        self.result = None
        self.equity_curve = None
        self.computed_metrics = None

    async def create(self, config, strategy_id) -> UUID:
        return uuid7()

    async def complete(self, backtest_id, result) -> None:
        self.result = result

    async def save_equity_curve(self, backtest_id, points) -> None:
        self.equity_curve = points

    async def save_computed_metrics(self, metrics) -> None:
        self.computed_metrics = metrics


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
    # _bar's open=high=low=close (no wick) makes ATR14 unavailable this early
    # (< 15 bars) -> tp=sl=entry_price exactly, so every entry is immediately
    # TP_HIT on the very next bar (price steps by 1 every bar here) and,
    # since is_in_trade goes False again before this SAME bar's signal
    # section runs, the always-firing _FakeStrategy re-enters same-bar too
    # (Rule 2 only forbids a new entry WHILE still in a trade — it does not
    # forbid a fresh entry the instant a trade closes). Net: bars 1-3 each
    # do an exit+re-entry (2 fills), bar 4 (last) does an exit+re-entry+
    # END_OF_DATA close of that fresh position (3 fills) -> 4+4+... see
    # inline count below; signals_generated stays 4 (one generate_signals
    # call per bar while flat, same as before this rule set existed).
    bars = [_bar(i, str(100 + i)) for i in range(5)]
    execution = _FakeExecution()
    engine = _engine(bars, execution)
    _bt_id, result = await engine.run(_config(), strategy_id=uuid4(), portfolio_id=uuid4())
    assert result.bars_processed == 5
    assert result.signals_generated == 4
    assert result.orders_created == result.orders_filled == execution.calls == 8
    assert len(execution.exit_calls) == 4  # every exit carries Rule 4's trade-result fields
    assert all(c["exit_reason"] in ("TP_HIT", "END_OF_DATA") for c in execution.exit_calls)


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


# ── Rule 2 (one-trade-at-a-time) / Rule 3 (TP/SL exit) ──────────────────────
# A real (non-degenerate) ATR needs >=15 bars of history, so these tests use
# a strategy that only fires while the view is 16-20 bars long: bar index 15
# is the entry (first bar with real ATR available), 16-19 are HELD bars where
# the strategy fires again every time but the engine must SKIP (Rule 2) since
# a trade is open, and bar 20 is engineered to hit TP/SL (or not, for the
# "still open" control) with the strategy deliberately silent so the test
# isolates the TP/SL check from any same-bar re-entry.


def _wick_bar(i: int, close: float, high: float, low: float) -> OHLCVBar:
    return OHLCVBar(
        asset_id=uuid4(), interval="1h", ts=_T0 + timedelta(hours=i),
        open=Decimal(str(close)), high=Decimal(str(high)), low=Decimal(str(low)),
        close=Decimal(str(close)), volume=Decimal("1"), vwap=None, trade_count=None,
        adjustment_factor=None, data_quality=Decimal("1"), source="test",
    )


def _atr_setup_bars() -> list[OHLCVBar]:
    # i=0..15: alternating 100/102 close, constant wick +-1 -> constant
    # True Range = 3 for every step -> ATR14 = 3 exactly (see test_trade_rules.py
    # for the same closed-form check on the pure function).
    return [_wick_bar(i, 102 if i % 2 else 100, (102 if i % 2 else 100) + 1, (102 if i % 2 else 100) - 1)
            for i in range(16)]


class _WindowedFakeStrategy(Strategy):
    """Fires a fixed long signal only while the point-in-time view is 16-20
    bars long — isolates one entry (bar 15) + several held bars (16-19) from
    the TP/SL bar (20), where this strategy is deliberately silent.
    """

    async def generate_signals(self, view, config):
        bars = await view.latest_bars(_ASSET, "1h", limit=1000)
        if 16 <= len(bars) <= 20:
            return [Signal(asset=_ASSET, value=Decimal("0.5"), ts=bars[-1].ts, metadata={})]
        return []


def _windowed_engine(bars: list[OHLCVBar], execution: "_FakeExecution"):
    return BacktestEngine(
        bars=_FakeBars(bars), assets=_FakeAssets(uuid4()), positions=_FakePositions(),
        backtests=_FakeBacktests(), signal_recorder=_FakeSignalRecorder(),
        sizer=LinearConvictionSizer(), constructor=WeightedSumConstructor(),
        order_gen=_FakeOrderGen(), execution=execution,
        strategy_plugin=_WindowedFakeStrategy(),
    )


@pytest.mark.asyncio
async def test_one_trade_at_a_time_skips_signal_while_in_trade() -> None:
    setup = _atr_setup_bars()  # i=0..15
    held = [_wick_bar(i, 101, 101.5, 100.5) for i in range(16, 20)]  # i=16..19, well inside [96,111]
    bars = setup + held  # 20 bars total, entry at i=15, held through i=19
    execution = _FakeExecution()
    _bt_id, result = await _windowed_engine(bars, execution).run(
        _config_for(bars), strategy_id=uuid4(), portfolio_id=uuid4(),
    )
    # Rule 2 gates signal generation itself while in a trade — the engine
    # never even CALLS generate_signals for i=16..19 (a stronger skip than
    # generating and discarding), so signals_generated stays at 1 despite
    # the strategy being willing to fire on all 4 of those held bars.
    # No TP/SL bar follows, so the trade is still open when the replay runs
    # out of bars -> one END_OF_DATA close, not a fabricated extra fill.
    assert result.signals_generated == 1
    assert result.orders_created == 2   # entry + END_OF_DATA close
    assert result.orders_filled == 2
    assert execution.calls == 2
    assert execution.exit_calls[0]["exit_reason"] == "END_OF_DATA"


@pytest.mark.asyncio
async def test_tp_hit_exits_trade_and_resets_is_in_trade() -> None:
    setup = _atr_setup_bars()
    held = [_wick_bar(i, 101, 101.5, 100.5) for i in range(16, 20)]
    # entry_price=102 (bar 15, odd index -> 102), ATR=3 -> tp=102+9=111, sl=102-6=96.
    # bar 20: high=113 clears tp=111; low=111 does NOT clear sl=96 -> TP_HIT only.
    tp_bar = [_wick_bar(20, 112, 113, 111)]
    bars = setup + held + tp_bar  # 21 bars, strategy silent at i=20 (view len 21)
    execution = _FakeExecution()
    _bt_id, result = await _windowed_engine(bars, execution).run(
        _config_for(bars), strategy_id=uuid4(), portfolio_id=uuid4(),
    )
    # entry (i=15) + exit (i=20) = 2 orders/fills; no END_OF_DATA close needed
    # since the trade already closed via TP before the replay ran out of bars.
    assert result.orders_created == 2
    assert result.orders_filled == 2
    assert len(execution.exit_calls) == 1
    exit_call = execution.exit_calls[0]
    assert exit_call["exit_reason"] == "TP_HIT"
    assert exit_call["price_return_pct"] == (Decimal("111") - Decimal("102")) / Decimal("102") * Decimal("100")


@pytest.mark.asyncio
async def test_sl_hit_exits_trade_and_resets_is_in_trade() -> None:
    setup = _atr_setup_bars()
    held = [_wick_bar(i, 101, 101.5, 100.5) for i in range(16, 20)]
    # Same entry/tp/sl as the TP test (102 / 111 / 96). bar 20: low=95 clears
    # sl=96; high=97 does NOT clear tp=111 -> SL_HIT only.
    sl_bar = [_wick_bar(20, 96, 97, 95)]
    bars = setup + held + sl_bar
    execution = _FakeExecution()
    _bt_id, result = await _windowed_engine(bars, execution).run(
        _config_for(bars), strategy_id=uuid4(), portfolio_id=uuid4(),
    )
    assert result.orders_created == 2
    assert result.orders_filled == 2
    assert len(execution.exit_calls) == 1
    exit_call = execution.exit_calls[0]
    assert exit_call["exit_reason"] == "SL_HIT"
    assert exit_call["price_return_pct"] == (Decimal("96") - Decimal("102")) / Decimal("102") * Decimal("100")


def _config_for(bars: list[OHLCVBar]) -> BacktestConfig:
    return BacktestConfig(
        name="rule-test", symbol="BTC/USDT", exchange="binance", asset_class="crypto",
        interval="1h", strategy_config={}, start=bars[0].ts, end=bars[-1].ts,
        initial_capital=Decimal("100000"), max_position_pct=Decimal("0.10"),
    )

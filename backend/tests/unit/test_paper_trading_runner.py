# Governing specification: Doc 14 §10.5 (Paper Trading) — §10.5.4 (Paper-Live
#   Parity), §10.5.5 (Real-Time Market Data / new-bar detection), §10.5.7
#   (running P&L + per-bar state), §10.5.8 (paper-vs-backtest comparison),
#   §10.5.10 (artifacts). F-20 (daily reset), T-3.
# Per Doc 00 §14.11
#
# Step 5.2/5.3 — PaperTradingRunner loop + lifecycle semantics with fakes for
# every collaborator (no DB). The real live-path pipeline reuse (the shared
# TradingCycle over real Sizing/Construction/Order/Risk/Execution) and the real
# F-20 reset SQL are proven end-to-end in the live verification; here we pin the
# RUNNER's own contract: watermark seeding, new-bar detection, gap no-op,
# per-bar session update, the UTC-midnight daily reset with lifetime carry, the
# single-number comparison, and the STOPPED transition.
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from quant_hub.application.paper_trading.runner import (
    PaperCycleContext,
    PaperTradingRunner,
)
from quant_hub.application.trading.cycle import CycleStepOutcome
from quant_hub.domain.market_data.entities import AssetRef, OHLCVBar
from quant_hub.domain.portfolio.sizing import SizingConstraints

_ASSET = AssetRef(symbol="BTC/USDT", exchange="binance", asset_class="crypto")
_SEED = datetime(2026, 7, 6, 22, 0, tzinfo=timezone.utc)
_DAY1 = datetime(2026, 7, 6, 23, 0, tzinfo=timezone.utc)  # UTC day 6
_DAY2 = datetime(2026, 7, 7, 0, 0, tzinfo=timezone.utc)  # UTC day 7 — crosses midnight
_ASSET_ID = uuid4()


def _bar(ts: datetime, close: str) -> OHLCVBar:
    return OHLCVBar(
        asset_id=_ASSET_ID, interval="1h", ts=ts,
        open=Decimal(close), high=Decimal(close), low=Decimal(close), close=Decimal(close),
        volume=Decimal("1"), vwap=None, trade_count=None, adjustment_factor=None,
        data_quality=Decimal("1"), source="test",
    )


@dataclass
class _Pos:
    realized_pnl_today: Decimal
    unrealized_pnl: Decimal


class _FakeUoW:
    def __init__(self, log: list[str]) -> None:
        self._log = log

    async def __aenter__(self) -> "_FakeUoW":
        return self

    async def __aexit__(self, *exc: object) -> bool:
        return False

    async def commit(self) -> None:
        self._log.append("commit")


class _FakeBars:
    def __init__(self, ts_schedule: list[datetime | None], close: str = "100") -> None:
        self._ts = ts_schedule
        self._n = 0
        self._last: datetime | None = None
        self.close = Decimal(close)

    async def get_latest_ts(self, asset_id: object, interval: str) -> datetime | None:
        self._last = self._ts[min(self._n, len(self._ts) - 1)]
        self._n += 1
        return self._last

    async def get_bars(self, asset_id: object, interval: str, limit: int = 100) -> list[OHLCVBar]:
        return [] if self._last is None else [_bar(self._last, str(self.close))]


class _FakeAssets:
    async def get_by_symbol_exchange(self, symbol: str, exchange: str) -> object:
        return _ASSET_ID


class _FakePositions:
    """Stateful position store: `realized_today` accumulates within a day (the
    fake cycle adds to it per step, like a real fill), and reset_realized_pnl_today
    zeroes it while returning the folded sum — exactly the F-20 contract."""

    def __init__(self, realized: str = "0", unrealized: str = "0") -> None:
        self.realized_today = Decimal(realized)
        self.unrealized = Decimal(unrealized)
        self.reset_calls = 0

    async def get_by_portfolio(self, portfolio_id: object) -> list[_Pos]:
        return [_Pos(self.realized_today, self.unrealized)]

    async def get_by_portfolio_and_asset(self, portfolio_id: object, asset_id: object) -> _Pos:
        return _Pos(self.realized_today, self.unrealized)

    async def reset_realized_pnl_today(self, portfolio_id: object) -> Decimal:
        self.reset_calls += 1
        folded = self.realized_today
        self.realized_today = Decimal("0")
        return folded


class _FakeSessions:
    def __init__(self) -> None:
        self.updates: list[dict] = []

    async def update_runtime(self, session_id: object, **kwargs: object) -> None:
        self.updates.append(kwargs)


class _FakeBacktests:
    def __init__(self, total_return: str | None) -> None:
        self._total_return = total_return

    async def get_by_id(self, backtest_id: object) -> dict | None:
        return {"id": backtest_id, "total_return": self._total_return}


class _FakeCycle:
    def __init__(self, outcome: CycleStepOutcome, positions: _FakePositions, realize: str = "0") -> None:
        self.calls: list[dict] = []
        self._outcome = outcome
        self._positions = positions
        self._realize = Decimal(realize)

    async def run_step(self, **kwargs: object) -> CycleStepOutcome:
        self.calls.append(kwargs)
        self._positions.realized_today += self._realize  # simulate a realizing fill
        return self._outcome


def _outcome(**kw: int) -> CycleStepOutcome:
    base = dict(signals_generated=0, orders_created=0, orders_filled=0, orders_rejected=0)
    base.update(kw)
    return CycleStepOutcome(fills=(), **base)  # type: ignore[arg-type]


def _runner(bars, cycle, sessions, positions, backtests=None):
    log: list[str] = []
    ctx = PaperCycleContext(
        cycle=cycle, sessions=sessions, bars=bars, assets=_FakeAssets(),
        positions=positions, backtests=backtests or _FakeBacktests(None), view=object(),
    )

    async def _no_sleep(_seconds: float) -> None:
        return None

    runner = PaperTradingRunner(
        session_factory=lambda: _FakeUoW(log),
        wire=lambda _uow: ctx,
        poll_interval_seconds=0.0,
        sleep=_no_sleep,
        now=lambda: _DAY2,
    )
    return runner, log


async def _run(runner, **kw):
    defaults = dict(
        session_id=uuid4(), strategy_id=uuid4(), portfolio_id=uuid4(),
        asset=_ASSET, interval="1h", portfolio_value=Decimal("100000"),
        initial_capital=Decimal("100000"), strategy_config={"symbol": "BTC/USDT"},
        constraints=SizingConstraints(max_position_pct=Decimal("0.10")),
    )
    defaults.update(kw)
    return await runner.run(**defaults)


@pytest.mark.asyncio
async def test_new_bar_drives_one_step_and_updates_session() -> None:
    bars = _FakeBars([_SEED, _DAY1], close="105")
    positions = _FakePositions()
    cycle = _FakeCycle(_outcome(signals_generated=1, orders_created=1, orders_filled=1), positions)
    sessions = _FakeSessions()
    runner, log = _runner(bars, cycle, sessions, positions)

    summary = await _run(runner, max_bars=1)

    assert summary.bars_processed == 1 and summary.orders_filled == 1
    assert summary.stop_reason == "max_bars"
    assert summary.last_bar_ts == _DAY1.isoformat()
    assert cycle.calls[0]["price"] == Decimal("105") and cycle.calls[0]["timestamp"] == _DAY1
    # first bar sets the accounting day but does NOT reset
    assert positions.reset_calls == 0
    assert sessions.updates[0]["last_pnl_reset_at"] is None
    assert sessions.updates[-1]["status"] == "STOPPED" and sessions.updates[-1]["ended_at"] == _DAY2
    assert log.count("commit") == 2  # one per-bar commit + one finalize commit


@pytest.mark.asyncio
async def test_utc_day_boundary_resets_daily_pnl_while_lifetime_accumulates() -> None:
    # day-1 bar realizes +50; day-2 bar crosses UTC midnight -> reset, then +50 again
    bars = _FakeBars([_SEED, _DAY1, _DAY2])
    positions = _FakePositions()
    cycle = _FakeCycle(_outcome(orders_filled=1), positions, realize="50")
    sessions = _FakeSessions()
    runner, _log = _runner(bars, cycle, sessions, positions)

    summary = await _run(runner, max_bars=2)

    assert summary.bars_processed == 2
    assert summary.daily_resets == 1 and positions.reset_calls == 1
    # DAILY figure was reset and re-accumulated the new day's 50 (not 100)
    assert positions.realized_today == Decimal("50")
    # LIFETIME retained day-1's 50 (carried) + day-2's 50 = 100
    assert summary.realized_pnl == "100"
    # the day-1 update carried no reset; the day-2 update stamped the boundary
    assert sessions.updates[0]["last_pnl_reset_at"] is None
    assert sessions.updates[1]["last_pnl_reset_at"] == _DAY2  # UTC midnight of day 7
    assert sessions.updates[1]["realized_pnl"] == Decimal("100")
    # results JSONB carries the carry + reset count for the graduation check
    assert sessions.updates[1]["results"]["realized_pnl_carried"] == "50"
    assert sessions.updates[1]["results"]["daily_resets"] == 1


@pytest.mark.asyncio
async def test_startup_watermark_does_not_retrade_the_pre_existing_bar() -> None:
    bars = _FakeBars([_SEED, _SEED])
    positions = _FakePositions()
    cycle = _FakeCycle(_outcome(), positions)
    sessions = _FakeSessions()
    runner, _log = _runner(bars, cycle, sessions, positions)

    summary = await _run(runner, max_polls=2)

    assert summary.bars_processed == 0 and cycle.calls == []
    assert summary.stop_reason == "max_polls"
    assert sessions.updates[-1]["status"] == "STOPPED"


@pytest.mark.asyncio
async def test_gap_when_no_bar_yet_is_a_noop_not_an_error() -> None:
    bars = _FakeBars([None, None, None])
    positions = _FakePositions()
    cycle = _FakeCycle(_outcome(), positions)
    sessions = _FakeSessions()
    runner, _log = _runner(bars, cycle, sessions, positions)

    summary = await _run(runner, max_polls=3)

    assert summary.bars_processed == 0 and cycle.calls == []
    assert summary.last_bar_ts is None


@pytest.mark.asyncio
async def test_stop_event_requests_graceful_stop() -> None:
    import asyncio

    bars = _FakeBars([_SEED, _DAY1])
    positions = _FakePositions()
    cycle = _FakeCycle(_outcome(), positions)
    sessions = _FakeSessions()
    runner, _log = _runner(bars, cycle, sessions, positions)

    stop = asyncio.Event()
    stop.set()
    summary = await _run(runner, stop_event=stop)

    assert summary.bars_processed == 0 and summary.stop_reason == "stop_requested"
    assert sessions.updates[-1]["status"] == "STOPPED"


@pytest.mark.asyncio
async def test_comparison_figure_computes_against_linked_backtest() -> None:
    # paper realizes +100 on 1000 capital -> paper_total_return 0.10; backtest 0.04
    bars = _FakeBars([_SEED, _DAY1])
    positions = _FakePositions()
    cycle = _FakeCycle(_outcome(orders_filled=1), positions, realize="100")
    sessions = _FakeSessions()
    backtests = _FakeBacktests(total_return="0.04")
    runner, _log = _runner(bars, cycle, sessions, positions, backtests)

    bt_id = uuid4()
    summary = await _run(runner, initial_capital=Decimal("1000"), backtest_id=bt_id, max_bars=1)

    assert summary.paper_total_return == "0.1"
    assert summary.total_return_deviation == "0.06"  # 0.10 - 0.04
    comp = sessions.updates[-1]["results"]["comparison"]
    assert comp["backtest_id"] == str(bt_id)
    assert comp["backtest_total_return"] == "0.04" and comp["paper_total_return"] == "0.1"


@pytest.mark.asyncio
async def test_comparison_is_null_without_a_linked_backtest() -> None:
    bars = _FakeBars([_SEED, _DAY1])
    positions = _FakePositions()
    cycle = _FakeCycle(_outcome(), positions, realize="10")
    sessions = _FakeSessions()
    runner, _log = _runner(bars, cycle, sessions, positions)

    summary = await _run(runner, max_bars=1)  # no backtest_id

    assert summary.total_return_deviation is None
    assert sessions.updates[-1]["results"]["comparison"] is None

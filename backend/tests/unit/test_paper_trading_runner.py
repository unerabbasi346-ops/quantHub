# Governing specification: Doc 14 §10.5 (Paper Trading) — §10.5.4 (Paper-Live
#   Parity), §10.5.5 (Real-Time Market Data / new-bar detection), §10.5.7
#   (running P&L + per-bar state). T-3.
# Per Doc 00 §14.11
#
# Step 5.2 — PaperTradingRunner loop semantics with fakes for every
# collaborator (no DB). The real live-path pipeline reuse (the shared
# TradingCycle over real Sizing/Construction/Order/Risk/Execution) is proven
# end-to-end in the live verification; here we pin the RUNNER's own contract:
# watermark seeding, new-bar detection, gap no-op, per-bar session update, and
# the STOPPED transition.
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
_T0 = datetime(2026, 7, 6, 12, 0, tzinfo=timezone.utc)
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
    """get_latest_ts returns the next scripted timestamp on each call (the seed
    read consumes the first); get_bars returns the newest bar at the last ts
    get_latest_ts handed out."""

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
    def __init__(self, pos: _Pos | None) -> None:
        self._pos = pos

    async def get_by_portfolio_and_asset(self, portfolio_id: object, asset_id: object) -> _Pos | None:
        return self._pos


class _FakeSessions:
    def __init__(self) -> None:
        self.updates: list[dict] = []

    async def update_runtime(self, session_id: object, **kwargs: object) -> None:
        self.updates.append(kwargs)


class _FakeCycle:
    def __init__(self, outcome: CycleStepOutcome) -> None:
        self.calls: list[dict] = []
        self._outcome = outcome

    async def run_step(self, **kwargs: object) -> CycleStepOutcome:
        self.calls.append(kwargs)
        return self._outcome


def _outcome(**kw: int) -> CycleStepOutcome:
    base = dict(signals_generated=0, orders_created=0, orders_filled=0, orders_rejected=0)
    base.update(kw)
    return CycleStepOutcome(fills=(), **base)  # type: ignore[arg-type]


def _runner(bars: _FakeBars, cycle: _FakeCycle, sessions: _FakeSessions, positions: _FakePositions):
    log: list[str] = []
    ctx = PaperCycleContext(
        cycle=cycle, sessions=sessions, bars=bars, assets=_FakeAssets(),
        positions=positions, view=object(),  # view is only handed to the (fake) cycle
    )

    async def _no_sleep(_seconds: float) -> None:
        return None

    runner = PaperTradingRunner(
        session_factory=lambda: _FakeUoW(log),
        wire=lambda _uow: ctx,
        poll_interval_seconds=0.0,
        sleep=_no_sleep,
        now=lambda: _T0,
    )
    return runner, log


async def _run(runner, **kw):
    return await runner.run(
        session_id=uuid4(), strategy_id=uuid4(), portfolio_id=uuid4(),
        asset=_ASSET, interval="1h", portfolio_value=Decimal("100000"),
        strategy_config={"symbol": "BTC/USDT"},
        constraints=SizingConstraints(max_position_pct=Decimal("0.10")),
        **kw,
    )


@pytest.mark.asyncio
async def test_new_bar_drives_one_step_and_updates_session() -> None:
    # seed watermark = _T0; next poll sees _T0+1h (a new bar) -> exactly one step
    bars = _FakeBars([_T0, _T0 + timedelta(hours=1)], close="105")
    cycle = _FakeCycle(_outcome(signals_generated=1, orders_created=1, orders_filled=1))
    sessions = _FakeSessions()
    positions = _FakePositions(_Pos(realized_pnl_today=Decimal("7"), unrealized_pnl=Decimal("3")))
    runner, log = _runner(bars, cycle, sessions, positions)

    summary = await _run(runner, max_bars=1)

    assert summary.bars_processed == 1
    assert summary.orders_filled == 1 and summary.signals_generated == 1
    assert summary.stop_reason == "max_bars"
    assert summary.last_bar_ts == (_T0 + timedelta(hours=1)).isoformat()
    # the step ran against the NEW bar's close + ts (live market context)
    assert len(cycle.calls) == 1
    assert cycle.calls[0]["price"] == Decimal("105")
    assert cycle.calls[0]["timestamp"] == _T0 + timedelta(hours=1)
    # per-bar session update carried the marked P&L, then a STOPPED update
    assert sessions.updates[0]["realized_pnl"] == Decimal("7")
    assert sessions.updates[0]["unrealized_pnl"] == Decimal("3")
    assert sessions.updates[-1]["status"] == "STOPPED"
    assert sessions.updates[-1]["ended_at"] == _T0
    assert log.count("commit") == 2  # one per-bar commit + one STOPPED commit


@pytest.mark.asyncio
async def test_startup_watermark_does_not_retrade_the_pre_existing_bar() -> None:
    # latest never advances past the seed -> the already-closed bar is NOT traded
    bars = _FakeBars([_T0, _T0])
    cycle = _FakeCycle(_outcome())
    sessions = _FakeSessions()
    runner, log = _runner(bars, cycle, sessions, _FakePositions(None))

    summary = await _run(runner, max_polls=2)

    assert summary.bars_processed == 0
    assert cycle.calls == []
    assert summary.stop_reason == "max_polls"
    # still transitions STOPPED (a started-then-stopped, no-bars session is valid)
    assert sessions.updates[-1]["status"] == "STOPPED"


@pytest.mark.asyncio
async def test_gap_when_no_bar_yet_is_a_noop_not_an_error() -> None:
    # get_latest_ts returns None (nothing ingested yet) -> no step, no raise
    bars = _FakeBars([None, None, None])
    cycle = _FakeCycle(_outcome())
    sessions = _FakeSessions()
    runner, _log = _runner(bars, cycle, sessions, _FakePositions(None))

    summary = await _run(runner, max_polls=3)

    assert summary.bars_processed == 0
    assert cycle.calls == []
    assert summary.last_bar_ts is None


@pytest.mark.asyncio
async def test_stop_event_requests_graceful_stop() -> None:
    import asyncio

    bars = _FakeBars([_T0, _T0 + timedelta(hours=1)])
    cycle = _FakeCycle(_outcome())
    sessions = _FakeSessions()
    runner, _log = _runner(bars, cycle, sessions, _FakePositions(None))

    stop = asyncio.Event()
    stop.set()  # already requested before the first iteration
    summary = await _run(runner, stop_event=stop)

    assert summary.bars_processed == 0
    assert summary.stop_reason == "stop_requested"
    assert sessions.updates[-1]["status"] == "STOPPED"


@pytest.mark.asyncio
async def test_flat_position_marks_zero_pnl() -> None:
    # no position yet after the step -> realized/unrealized default to 0
    bars = _FakeBars([_T0, _T0 + timedelta(hours=1)])
    cycle = _FakeCycle(_outcome(signals_generated=1, orders_created=1, orders_rejected=1))
    sessions = _FakeSessions()
    runner, _log = _runner(bars, cycle, sessions, _FakePositions(None))

    summary = await _run(runner, max_bars=1)

    assert summary.orders_rejected == 1 and summary.orders_filled == 0
    assert sessions.updates[0]["realized_pnl"] == Decimal("0")
    assert sessions.updates[0]["unrealized_pnl"] == Decimal("0")

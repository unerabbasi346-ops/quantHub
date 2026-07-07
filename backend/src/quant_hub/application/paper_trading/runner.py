# Governing specification: Doc 14 §10.5 (Paper Trading Architecture)
#   §10.5.4 (Paper-Live Parity / Same Signal Pipeline), §10.5.5 (Real-Time
#   Market Data Consumption), §10.5.7 (Paper Trading Monitoring — running P&L
#   and per-bar state), §10.5.8 (Paper vs Backtest Comparison), §10.5.10 (Paper
#   Trading Artifacts).
# Layer: Application — Doc 07 §Layers (orchestration only; no SQL, no session
#   construction of its own — collaborators are injected).
# Invariants: T-3 (Paper-Live Parity), P-13 (deterministic per-bar processing).
# Scope: handbook/KNOWN_LIMITATIONS.md — Phase 5 (paper trading); F-19 (no NAV
#   ledger — static portfolio_value); F-20 (realized_pnl_today daily reset,
#   RESOLVED for the paper path here).
# Per Doc 00 §14.11
#
# Step 5.2 — the Continuous Paper Trading Runner: the live-market analogue of
# the Step 3.7 BacktestEngine. Where the backtest REPLAYS a fixed historical
# range, this runner POLLS the governed market_data.ohlcv_bars store for the
# newest ingested bar (§10.5.5) and, each time a genuinely NEW bar arrives,
# drives EXACTLY ONE TradingCycle.run_step against it — the same shared
# Signal -> Construction -> Sizing -> Order -> Risk -> Fill -> Position handler
# the backtest drives, so paper and backtest logic cannot diverge (T-3, §10.5.4
# "Same Signal Pipeline"). It commits per bar and keeps the governing
# analytics.paper_trading_sessions record (Step 5.0) updated with running state.
#
# Step 5.3 — adds the session lifecycle pieces that build on that loop:
#   (1) F-20 daily reset — at each UTC-midnight day boundary the runner folds
#       the completed day's realized_pnl_today into a session-LIFETIME carry and
#       zeroes the daily figure (PositionRepository.reset_realized_pnl_today),
#       so the session's realized_pnl keeps accumulating correctly across days
#       while core.positions.realized_pnl_today reflects only "today" again.
#   (2) Paper-vs-backtest comparison (§10.5.8) — a single total-return deviation
#       figure between the session and its linked backtest_id, computed at stop.
#   (3) Session artifacts (§10.5.10) — the final results JSONB captures the
#       P&L, activity, reset, and comparison figures a Step 5.4 graduation check
#       (§10.5.9) will read.
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from quant_hub.application.trading.cycle import TradingCycle
from quant_hub.domain.backtesting.interfaces import BacktestRepository
from quant_hub.domain.market_data.entities import AssetRef
from quant_hub.domain.market_data.interfaces import AssetRepository, OHLCVRepository
from quant_hub.domain.paper_trading.interfaces import PaperTradingSessionRepository
from quant_hub.domain.portfolio.interfaces import PositionRepository
from quant_hub.domain.portfolio.sizing import SizingConstraints
from quant_hub.domain.strategy_engine.strategy import MarketDataView

_ZERO = Decimal("0")


class UnitOfWork(Protocol):
    """Structural contract for one atomic unit of work — satisfied by an
    SQLAlchemy AsyncSession (an async context manager exposing commit()).
    Typed here structurally so the application layer never imports the
    infrastructure session type (Doc 07 §Dependency Rules)."""

    async def commit(self) -> None: ...


# A factory that opens a FRESH unit of work (async context manager). `wire`
# maps that unit of work to the collaborators bound to it — the composition
# root lives in the caller (scripts/run_paper_session.py), never in this layer.
SessionFactory = Callable[[], AbstractAsyncContextManager[UnitOfWork]]


@dataclass(frozen=True)
class PaperCycleContext:
    """The wired collaborators for ONE unit of work, all bound to the same
    session. `cycle` and `positions` share the same PositionRepository instance
    so the runner can read the P&L the cycle just wrote (§10.5.7). `backtests`
    is read-only, used once at stop for the §10.5.8 comparison. Built by the
    injected `wire` callable — the runner constructs no repository itself."""

    cycle: TradingCycle
    sessions: PaperTradingSessionRepository
    bars: OHLCVRepository
    assets: AssetRepository
    positions: PositionRepository
    backtests: BacktestRepository
    view: MarketDataView


@dataclass
class _RunState:
    """Mutable per-invocation accounting — created fresh in each run() call so
    the runner is re-entrant. `realized_carried` (C) is the realized P&L folded
    from all COMPLETED days; the session-lifetime realized is always C + the
    current day's live realized_pnl_today, so it survives the F-20 daily reset.
    `current_day` is the UTC calendar day currently open (bar-timestamp driven,
    not wall-clock)."""

    totals: dict[str, int] = field(
        default_factory=lambda: {
            "bars_processed": 0,
            "signals_generated": 0,
            "orders_created": 0,
            "orders_filled": 0,
            "orders_rejected": 0,
        }
    )
    current_day: date | None = None
    realized_carried: Decimal = _ZERO
    daily_resets: int = 0
    realized_lifetime: Decimal = _ZERO  # C + today's realized (last marked)
    unrealized: Decimal = _ZERO  # last marked mark-to-market
    last_bar_ts: datetime | None = None


@dataclass(frozen=True)
class PaperRunSummary:
    """Terminal tally of a runner invocation — the return value the CLI prints;
    the fuller shape is mirrored into the session's `results` JSONB (§10.5.10).
    Decimal-valued fields are stringified so the summary is JSON-clean."""

    session_id: UUID
    bars_processed: int
    signals_generated: int
    orders_created: int
    orders_filled: int
    orders_rejected: int
    daily_resets: int
    realized_pnl: str
    unrealized_pnl: str
    paper_total_return: str
    total_return_deviation: str | None
    last_bar_ts: str | None
    stop_reason: str


class PaperTradingRunner:
    """Continuous live-market driver of the shared TradingCycle — Doc 14 §10.5.

    JUDGMENT CALLS (Doc 00 §14.5/§14.7 — flagged, not silently decided):

    - POLLING MECHANISM (Step 5.2, design Q1): the runner learns a new bar has
      arrived by reading the latest bar timestamp from the governed
      market_data.ohlcv_bars table (OHLCVRepository.get_latest_ts) — NOT by
      coupling to Phase 1's ingestion process. A "new bar" is the max ts
      advancing past the last ts this runner processed. This reads the same
      governed store §10.5.5 names, needs no message bus, and lets ingestion
      and paper trading run as independent processes at independent cadences.

    - PROCESS MODEL (Step 5.2, design Q2): a single long-running asyncio poll
      loop, one run_step per new bar — deliberately NOT a job-scheduling system
      (proportionate to a solo-developer platform per S-6/S-8). Start/stop is a
      thin CLI (scripts/run_paper_session.py), mirroring run_ingestion.py.

    - PER-BAR TRANSACTION (unit of work): each processed bar is one fresh
      session -> [day-boundary reset] -> run_step -> session-runtime update ->
      commit, the "the paper runner commits per bar" boundary. A day-boundary
      reset (below) is part of the SAME unit of work as the bar that crossed it,
      so the zeroing and the new day's first step commit atomically. The
      injected `wire` builds collaborators per unit of work; this runner owns
      only the loop, the poll, the reset boundary, and the transaction.

    - LATEST-BAR-ONLY (live semantics): on each new-bar detection the runner
      processes ONLY the newest bar; it never back-fills bars that closed while
      it was between polls — the T-3 boundary between paper (live) and backtest
      (historical replay).

    - STARTUP WATERMARK: seeded to the latest already-closed bar at start, so a
      session trades only bars that ARRIVE AFTER it starts.

    - GAP HANDLING (Step 5.2, design Q4): no bar yet, unregistered asset, or ts
      not advanced -> no-op, sleep, re-poll. The loop never raises on an absent
      or unchanged bar (§10.5.5, T-3).

    - F-20 DAILY RESET (Step 5.3) + RESET CONVENTION: realized_pnl_today is
      reset at a **UTC-midnight** day boundary. UTC is chosen over an
      exchange-session boundary per the platform's existing UTC-normalization
      convention (Doc 11 §4, Step 1.5 — all bar timestamps are UTC), and because
      the reference instrument (crypto, BTC/USDT) trades 24/7 with no session
      close to anchor to. The boundary is **bar-timestamp driven** (bar.ts's UTC
      date), not wall-clock: a new bar whose UTC date exceeds the open
      accounting day folds the completed day's realized_pnl_today into a
      session-lifetime carry, zeroes the daily figure across the portfolio, and
      advances last_pnl_reset_at to that day's UTC midnight — BEFORE the day's
      first step runs. Session realized_pnl (lifetime) = carry + today's live
      realized, so it is continuous across the reset instant.

    - F-19 INTERACTION WITH THE RESET (flagged): the daily reset touches ONLY
      the P&L figure realized_pnl_today; it does NOT feed back into
      portfolio_value, which stays static at initial_capital every step (F-19 —
      no authoritative NAV/cash ledger). With a real ledger the day's realized
      P&L would roll into equity and the next day's sizing would see a changed
      portfolio_value; here the two are decoupled, so the reset is a pure
      P&L-accounting reset with no equity feedback. Leverage/sizing figures
      remain only as correct as the static initial_capital input (F-19).

    - PAPER-VS-BACKTEST COMPARISON (Step 5.3, §10.5.8): a SINGLE total-return
      deviation figure (paper_total_return - backtest_total_return), computed at
      stop against the session's linked backtest_id. Full distribution / same-
      period comparison stays deferred (original scoping decision). The runner
      does NOT verify the linked backtest is for the same strategy/period — the
      backtest_id is a caller-supplied baseline; that alignment is a §10.5.9
      graduation-gate concern (Step 5.4). If no backtest is linked, the figure
      is null (honest — no baseline), never fabricated.

    - PORTFOLIO-WIDE P&L (§10.5.7): realized/unrealized are summed across ALL
      the portfolio's positions, not just the traded asset — a session's P&L is
      portfolio-wide (identical to the single-asset case for the reference
      strategy, but correct for a multi-asset session).
    """

    def __init__(
        self,
        *,
        session_factory: SessionFactory,
        wire: Callable[[UnitOfWork], PaperCycleContext],
        poll_interval_seconds: float = 15.0,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self._session_factory = session_factory
        self._wire = wire
        self._poll_interval = poll_interval_seconds
        self._sleep = sleep
        self._now = now

    async def run(
        self,
        *,
        session_id: UUID,
        strategy_id: UUID,
        portfolio_id: UUID,
        asset: AssetRef,
        interval: str,
        portfolio_value: Decimal,
        initial_capital: Decimal,
        strategy_config: Mapping[str, object],
        constraints: SizingConstraints,
        backtest_id: UUID | None = None,
        max_bars: int | None = None,
        max_polls: int | None = None,
        stop_event: asyncio.Event | None = None,
    ) -> PaperRunSummary:
        """Drive the session until a stop condition, then finalize it (STOPPED +
        §10.5.8 comparison + §10.5.10 artifacts). Stop conditions: `stop_event`
        set (user stop / SIGINT), `max_bars` bars processed, `max_polls` poll
        iterations elapsed, or an interrupt. `portfolio_value` is the per-step
        sizing input; `initial_capital` is the return denominator — the two
        coincide under F-19 (static equity). `backtest_id` is the §10.5.8
        baseline (optional)."""
        state = _RunState()
        stop_reason = "stopped"

        asset_id, watermark = await self._seed(asset, interval)

        polls = 0
        try:
            while True:
                if stop_event is not None and stop_event.is_set():
                    stop_reason = "stop_requested"
                    break
                if max_polls is not None and polls >= max_polls:
                    stop_reason = "max_polls"
                    break
                polls += 1

                if asset_id is None:
                    asset_id = await self._resolve_asset_id(asset)

                latest = await self._latest_ts(asset_id, interval) if asset_id is not None else None

                if latest is None or (watermark is not None and latest <= watermark):
                    await self._sleep(self._poll_interval)
                    continue

                assert asset_id is not None  # implied by latest is not None
                processed = await self._process_new_bar(
                    state=state,
                    session_id=session_id,
                    strategy_id=strategy_id,
                    portfolio_id=portfolio_id,
                    asset=asset,
                    asset_id=asset_id,
                    interval=interval,
                    portfolio_value=portfolio_value,
                    strategy_config=strategy_config,
                    constraints=constraints,
                )
                if processed is None:
                    await self._sleep(self._poll_interval)
                    continue

                watermark = processed
                if max_bars is not None and state.totals["bars_processed"] >= max_bars:
                    stop_reason = "max_bars"
                    break
        except (KeyboardInterrupt, asyncio.CancelledError):
            stop_reason = "interrupted"

        comparison = await self._finalize(
            session_id=session_id,
            backtest_id=backtest_id,
            initial_capital=initial_capital,
            state=state,
            stop_reason=stop_reason,
        )
        return PaperRunSummary(
            session_id=session_id,
            bars_processed=state.totals["bars_processed"],
            signals_generated=state.totals["signals_generated"],
            orders_created=state.totals["orders_created"],
            orders_filled=state.totals["orders_filled"],
            orders_rejected=state.totals["orders_rejected"],
            daily_resets=state.daily_resets,
            realized_pnl=str(state.realized_lifetime),
            unrealized_pnl=str(state.unrealized),
            paper_total_return=str(self._total_return(state, initial_capital)),
            total_return_deviation=(
                None if comparison is None else comparison["total_return_deviation"]
            ),
            last_bar_ts=state.last_bar_ts.isoformat() if state.last_bar_ts is not None else None,
            stop_reason=stop_reason,
        )

    # ── internal helpers (each its own short-lived unit of work) ────────────

    async def _seed(
        self, asset: AssetRef, interval: str
    ) -> tuple[UUID | None, datetime | None]:
        async with self._session_factory() as uow:
            ctx = self._wire(uow)
            asset_id = await ctx.assets.get_by_symbol_exchange(asset.symbol, asset.exchange)
            watermark = (
                await ctx.bars.get_latest_ts(asset_id, interval) if asset_id is not None else None
            )
            return asset_id, watermark

    async def _resolve_asset_id(self, asset: AssetRef) -> UUID | None:
        async with self._session_factory() as uow:
            ctx = self._wire(uow)
            return await ctx.assets.get_by_symbol_exchange(asset.symbol, asset.exchange)

    async def _latest_ts(self, asset_id: UUID, interval: str) -> datetime | None:
        async with self._session_factory() as uow:
            ctx = self._wire(uow)
            return await ctx.bars.get_latest_ts(asset_id, interval)

    async def _process_new_bar(
        self,
        *,
        state: _RunState,
        session_id: UUID,
        strategy_id: UUID,
        portfolio_id: UUID,
        asset: AssetRef,
        asset_id: UUID,
        interval: str,
        portfolio_value: Decimal,
        strategy_config: Mapping[str, object],
        constraints: SizingConstraints,
    ) -> datetime | None:
        """The per-bar unit of work: (optional) day-boundary reset -> one step
        against the newest bar -> session running-state update -> commit.
        Returns the bar ts processed, or None if the newest bar vanished."""
        async with self._session_factory() as uow:
            ctx = self._wire(uow)
            newest = await ctx.bars.get_bars(asset_id, interval, limit=1)
            if not newest:
                return None
            bar = newest[-1]
            bar_day = bar.ts.astimezone(timezone.utc).date()

            # F-20 UTC-midnight reset (§10.5.7): a bar whose UTC date exceeds the
            # open accounting day folds the completed day's realized into the
            # lifetime carry and zeroes today's figure BEFORE the day's first
            # step — all within this same committed unit of work.
            reset_at: datetime | None = None
            if state.current_day is not None and bar_day > state.current_day:
                folded = await ctx.positions.reset_realized_pnl_today(portfolio_id)
                state.realized_carried += folded
                state.daily_resets += 1
                reset_at = datetime(bar_day.year, bar_day.month, bar_day.day, tzinfo=timezone.utc)
            state.current_day = bar_day

            # The paper step's market context is the newest bar's close + ts —
            # the live analogue of the backtest's (bar.close, bar.ts). The
            # strategy reads history through the LIVE view: that view difference
            # and this market context are the ONLY per-driver differences (T-3).
            outcome = await ctx.cycle.run_step(
                view=ctx.view,
                asset=asset,
                asset_id=asset_id,
                price=bar.close,
                timestamp=bar.ts,
                strategy_id=strategy_id,
                portfolio_id=portfolio_id,
                portfolio_value=portfolio_value,
                strategy_config=strategy_config,
                constraints=constraints,
            )
            state.totals["bars_processed"] += 1
            state.totals["signals_generated"] += outcome.signals_generated
            state.totals["orders_created"] += outcome.orders_created
            state.totals["orders_filled"] += outcome.orders_filled
            state.totals["orders_rejected"] += outcome.orders_rejected
            state.last_bar_ts = bar.ts

            # §10.5.7 running state: portfolio-wide mark-to-market. Lifetime
            # realized = carry (completed days) + today's live realized, so it is
            # unbroken across the reset above.
            realized_today, unrealized = await self._read_portfolio_pnl(ctx, portfolio_id)
            state.realized_lifetime = state.realized_carried + realized_today
            state.unrealized = unrealized
            await ctx.sessions.update_runtime(
                session_id,
                realized_pnl=state.realized_lifetime,
                unrealized_pnl=state.unrealized,
                last_pnl_reset_at=reset_at,
                results=self._results(state),
            )
            await uow.commit()
            return bar.ts

    async def _finalize(
        self,
        *,
        session_id: UUID,
        backtest_id: UUID | None,
        initial_capital: Decimal,
        state: _RunState,
        stop_reason: str,
    ) -> dict | None:
        """Transition the session to STOPPED with ended_at, the §10.5.8
        comparison (if a backtest is linked), and the §10.5.10 artifact snapshot
        a Step 5.4 graduation check reads. Returns the comparison dict or None."""
        async with self._session_factory() as uow:
            ctx = self._wire(uow)
            comparison = await self._compare_to_backtest(
                ctx, backtest_id, initial_capital, state
            )
            await ctx.sessions.update_runtime(
                session_id,
                status="STOPPED",
                ended_at=self._now(),
                results=self._results(
                    state,
                    stop_reason=stop_reason,
                    initial_capital=initial_capital,
                    comparison=comparison,
                ),
            )
            await uow.commit()
            return comparison

    async def _compare_to_backtest(
        self,
        ctx: PaperCycleContext,
        backtest_id: UUID | None,
        initial_capital: Decimal,
        state: _RunState,
    ) -> dict | None:
        """§10.5.8 single-number comparison: paper_total_return minus the linked
        backtest's total_return. None if unlinked or the backtest has no
        recorded total_return (not yet COMPLETED)."""
        if backtest_id is None:
            return None
        row = await ctx.backtests.get_by_id(backtest_id)
        if row is None or row.get("total_return") is None:
            return None
        backtest_return = Decimal(str(row["total_return"]))
        paper_return = self._total_return(state, initial_capital)
        return {
            "backtest_id": str(backtest_id),
            "backtest_total_return": str(backtest_return),
            "paper_total_return": str(paper_return),
            "total_return_deviation": str(paper_return - backtest_return),
        }

    @staticmethod
    async def _read_portfolio_pnl(
        ctx: PaperCycleContext, portfolio_id: UUID
    ) -> tuple[Decimal, Decimal]:
        positions = await ctx.positions.get_by_portfolio(portfolio_id)
        realized = sum((p.realized_pnl_today for p in positions), _ZERO)
        unrealized = sum((p.unrealized_pnl for p in positions), _ZERO)
        return realized, unrealized

    @staticmethod
    def _total_return(state: _RunState, initial_capital: Decimal) -> Decimal:
        """Paper total return = session-lifetime P&L / initial_capital. Under
        F-19 initial_capital is the static equity denominator (no NAV ledger)."""
        if initial_capital <= _ZERO:
            return _ZERO
        return (state.realized_lifetime + state.unrealized) / initial_capital

    def _results(
        self,
        state: _RunState,
        *,
        stop_reason: str | None = None,
        initial_capital: Decimal | None = None,
        comparison: dict | None = None,
    ) -> dict:
        """JSON-serializable running-state / artifact snapshot for the session
        `results` JSONB (§10.5.7 per-bar counters + live P&L; §10.5.10 final
        artifacts + §10.5.8 comparison a Step 5.4 graduation check reads). All
        Decimals are stringified — the repository json.dumps() this dict."""
        snapshot: dict = dict(state.totals)
        snapshot["last_bar_ts"] = (
            state.last_bar_ts.isoformat() if state.last_bar_ts is not None else None
        )
        snapshot["realized_pnl"] = str(state.realized_lifetime)
        snapshot["unrealized_pnl"] = str(state.unrealized)
        snapshot["realized_pnl_carried"] = str(state.realized_carried)
        snapshot["daily_resets"] = state.daily_resets
        if stop_reason is not None:
            snapshot["stop_reason"] = stop_reason
        if initial_capital is not None:
            snapshot["initial_capital"] = str(initial_capital)
            snapshot["paper_total_return"] = str(self._total_return(state, initial_capital))
        snapshot["comparison"] = comparison  # None when unlinked (§10.5.8)
        return snapshot

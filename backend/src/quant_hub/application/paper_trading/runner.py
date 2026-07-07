# Governing specification: Doc 14 §10.5 (Paper Trading Architecture)
#   §10.5.4 (Paper-Live Parity / Same Signal Pipeline), §10.5.5 (Real-Time
#   Market Data Consumption), §10.5.7 (Paper Trading Monitoring — running P&L
#   and per-bar state).
# Layer: Application — Doc 07 §Layers (orchestration only; no SQL, no session
#   construction of its own — collaborators are injected).
# Invariants: T-3 (Paper-Live Parity), P-13 (deterministic per-bar processing).
# Scope: handbook/KNOWN_LIMITATIONS.md — Phase 5 (paper trading); F-19 (no NAV
#   ledger); F-20 daily reset is NOT here (Step 5.3).
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
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from quant_hub.application.trading.cycle import TradingCycle
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
    so the runner can read the P&L the cycle just wrote (§10.5.7). Built by the
    injected `wire` callable — the runner constructs no repository itself."""

    cycle: TradingCycle
    sessions: PaperTradingSessionRepository
    bars: OHLCVRepository
    assets: AssetRepository
    positions: PositionRepository
    view: MarketDataView


@dataclass(frozen=True)
class PaperRunSummary:
    """Terminal tally of a runner invocation — the return value the CLI prints
    and the shape mirrored into the session's `results` JSONB (§10.5.10)."""

    session_id: UUID
    bars_processed: int
    signals_generated: int
    orders_created: int
    orders_filled: int
    orders_rejected: int
    last_bar_ts: str | None
    stop_reason: str


class PaperTradingRunner:
    """Continuous live-market driver of the shared TradingCycle — Doc 14 §10.5.

    JUDGMENT CALLS (Doc 00 §14.5/§14.7 — flagged, not silently decided):

    - POLLING MECHANISM (design Q1): the runner learns a new bar has arrived by
      reading the latest bar timestamp from the governed market_data.ohlcv_bars
      table (OHLCVRepository.get_latest_ts) — NOT by coupling to Phase 1's
      ingestion process. A "new bar" is the max ts advancing past the last ts
      this runner processed. This reads the same governed store §10.5.5 says
      paper trading consumes ("real-time market data through Doc 11 governed
      infrastructure"), needs no message bus / callback, and lets ingestion and
      paper trading run as independent processes at independent cadences.

    - PROCESS MODEL (design Q2): a single long-running asyncio poll loop, one
      run_step per new bar — deliberately NOT a job-scheduling system
      (proportionate to a solo-developer platform per S-6/S-8). Start/stop is a
      thin CLI (scripts/run_paper_session.py), mirroring run_ingestion.py.

    - PER-BAR TRANSACTION (unit of work): each processed bar is one fresh
      session -> run_step -> session-runtime update -> commit, exactly the
      "the paper runner commits per bar" boundary the Step 5.0 migration and
      the TradingCycle docstring anticipate. This mirrors run_ingestion.py's
      one-session-per-unit-of-work and avoids one hours-long
      idle-in-transaction connection. Polling reads use their own short-lived
      unit of work. The injected `wire` builds collaborators per unit of work;
      this runner owns only the loop, the poll, and the transaction boundary.

    - LATEST-BAR-ONLY (live semantics): on each new-bar detection the runner
      processes ONLY the newest bar; it never back-fills bars that closed while
      it was between polls. Trading a bar that already closed in the past is
      the backtest's job (historical replay), not live paper trading's — this
      is the T-3 boundary between the two drivers of the shared cycle.

    - STARTUP WATERMARK: the watermark is seeded to the latest already-closed
      bar at start, so a session trades only bars that ARRIVE AFTER it starts,
      never retroactively trading the last bar that closed before it began.

    - GAP HANDLING (design Q4): no bar yet, unregistered asset, or ts not
      advanced -> no-op, sleep, re-poll. The loop never raises on an absent or
      unchanged bar; a data gap affects paper trading by producing no step,
      exactly as it would stall live trading (§10.5.5, T-3).

    - PORTFOLIO VALUE (F-19): a static per-step portfolio_value (the session's
      initial_capital), identical to the backtest engine. There is no
      authoritative NAV/cash ledger yet (F-19, Doc 15 §11.4); leverage-based
      sizing is only as correct as this input.

    - SESSION P&L (§10.5.7): after each step the runner marks the session's
      realized/unrealized P&L from the position the cycle just maintained.
      Pre-F-20 (the daily reset is Step 5.3), positions.realized_pnl_today has
      not yet been reset, so it equals the session-lifetime realized figure;
      Step 5.3 introduces the reset and the lifetime/daily split the Step 5.0
      migration's realized_pnl column was sized for.
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
        strategy_config: Mapping[str, object],
        constraints: SizingConstraints,
        max_bars: int | None = None,
        max_polls: int | None = None,
        stop_event: asyncio.Event | None = None,
    ) -> PaperRunSummary:
        """Drive the session until a stop condition, then transition it to
        STOPPED. Stop conditions: `stop_event` set (user stop / SIGINT),
        `max_bars` bars processed, `max_polls` poll iterations elapsed, or an
        interrupt. `max_bars`/`max_polls` bound finite/test runs; an indefinite
        session (§10.5.3 "indefinite sessions permitted") passes neither and
        stops via `stop_event`.
        """
        totals = {
            "bars_processed": 0,
            "signals_generated": 0,
            "orders_created": 0,
            "orders_filled": 0,
            "orders_rejected": 0,
        }
        last_bar_ts: datetime | None = None
        stop_reason = "stopped"

        # Resolve the asset and seed the watermark to the current latest bar,
        # read-only. asset_id may be None (nothing ingested yet) — a valid
        # start; the loop resolves it once a later ingestion registers the asset.
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

                # Gap / no advance -> wait and re-poll (never errors). A first
                # bar appearing while watermark is None is NOT a gap: it falls
                # through to processing below.
                if latest is None or (watermark is not None and latest <= watermark):
                    await self._sleep(self._poll_interval)
                    continue

                assert asset_id is not None  # implied by latest is not None
                processed = await self._process_new_bar(
                    session_id=session_id,
                    strategy_id=strategy_id,
                    portfolio_id=portfolio_id,
                    asset=asset,
                    asset_id=asset_id,
                    interval=interval,
                    portfolio_value=portfolio_value,
                    strategy_config=strategy_config,
                    constraints=constraints,
                    totals=totals,
                )
                if processed is None:
                    # The MAX(ts) advanced but the row could not be fetched
                    # (e.g. deleted between the two reads) — treat as a gap.
                    await self._sleep(self._poll_interval)
                    continue

                last_bar_ts = processed
                watermark = processed
                if max_bars is not None and totals["bars_processed"] >= max_bars:
                    stop_reason = "max_bars"
                    break
        except (KeyboardInterrupt, asyncio.CancelledError):
            # Ctrl-C during an await (or task cancellation) is a graceful stop,
            # not a crash — fall through to the STOPPED transition below.
            stop_reason = "interrupted"

        await self._mark_stopped(session_id, totals, last_bar_ts, stop_reason)
        return PaperRunSummary(
            session_id=session_id,
            bars_processed=totals["bars_processed"],
            signals_generated=totals["signals_generated"],
            orders_created=totals["orders_created"],
            orders_filled=totals["orders_filled"],
            orders_rejected=totals["orders_rejected"],
            last_bar_ts=last_bar_ts.isoformat() if last_bar_ts is not None else None,
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
        session_id: UUID,
        strategy_id: UUID,
        portfolio_id: UUID,
        asset: AssetRef,
        asset_id: UUID,
        interval: str,
        portfolio_value: Decimal,
        strategy_config: Mapping[str, object],
        constraints: SizingConstraints,
        totals: dict[str, int],
    ) -> datetime | None:
        """Process exactly one step against the newest bar, update the session's
        running state, and commit — the per-bar unit of work. Returns the bar ts
        processed, or None if the newest bar could not be fetched."""
        async with self._session_factory() as uow:
            ctx = self._wire(uow)
            newest = await ctx.bars.get_bars(asset_id, interval, limit=1)
            if not newest:
                return None
            bar = newest[-1]

            # The paper step's market context is the newest bar's close + ts —
            # the live analogue of the backtest's (bar.close, bar.ts). The
            # strategy reads history through the LIVE view (latest N bars), not a
            # point-in-time historical slice: that view difference and this
            # market context are the ONLY per-driver differences (§10.5.4, T-3).
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
            totals["bars_processed"] += 1
            totals["signals_generated"] += outcome.signals_generated
            totals["orders_created"] += outcome.orders_created
            totals["orders_filled"] += outcome.orders_filled
            totals["orders_rejected"] += outcome.orders_rejected

            # §10.5.7 running state: mark-to-market P&L from the position the
            # cycle just maintained + per-bar monitoring counters in results.
            pos = await ctx.positions.get_by_portfolio_and_asset(portfolio_id, asset_id)
            realized = pos.realized_pnl_today if pos is not None else _ZERO
            unrealized = pos.unrealized_pnl if pos is not None else _ZERO
            await ctx.sessions.update_runtime(
                session_id,
                realized_pnl=realized,
                unrealized_pnl=unrealized,
                results=self._results(totals, bar.ts),
            )
            await uow.commit()
            return bar.ts

    async def _mark_stopped(
        self,
        session_id: UUID,
        totals: dict[str, int],
        last_bar_ts: datetime | None,
        stop_reason: str,
    ) -> None:
        """Transition the session to STOPPED with ended_at set and the final
        results snapshot — the §10.5 lifecycle close for this step (GRADUATED /
        the promotion gate is Step 5.4)."""
        async with self._session_factory() as uow:
            ctx = self._wire(uow)
            await ctx.sessions.update_runtime(
                session_id,
                status="STOPPED",
                ended_at=self._now(),
                results=self._results(totals, last_bar_ts, stop_reason=stop_reason),
            )
            await uow.commit()

    @staticmethod
    def _results(
        totals: dict[str, int],
        last_bar_ts: datetime | None,
        *,
        stop_reason: str | None = None,
    ) -> dict:
        """JSON-serializable running-state snapshot for the session `results`
        JSONB (§10.5.7 per-bar counters, §10.5.10 artifacts)."""
        snapshot: dict = dict(totals)
        snapshot["last_bar_ts"] = last_bar_ts.isoformat() if last_bar_ts is not None else None
        if stop_reason is not None:
            snapshot["stop_reason"] = stop_reason
        return snapshot

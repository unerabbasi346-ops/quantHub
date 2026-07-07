#!/usr/bin/env python
# Governing specification: Doc 14 §10.5 (Paper Trading Architecture) — §10.5.3
#   (Paper Trading Configuration / session record), §10.5.4 (Paper-Live Parity),
#   §10.5.5 (Real-Time Market Data Consumption).
#   Doc 04 — Repository Structure (QH-004): scripts/ = "Automation utilities";
#   "No business logic inside scripts/" — this script only wires
#   already-implemented backend components together (the composition root for
#   the PaperTradingRunner) and prints results, mirroring
#   scripts/run_ingestion.py (Step 1.4) and scripts/run_reference_strategy.py
#   (Step 2.4). The runner's LOGIC lives in application/paper_trading/runner.py.
# Per Doc 00 §14.11
#
# Step 5.2: start/stop control for a continuous paper trading session. Registers
# the strategy under test, ensures a PAPER portfolio, opens a governed
# analytics.paper_trading_sessions record (RUNNING), then drives the
# PaperTradingRunner against LIVE ingested bars until stopped (Ctrl-C, or a
# bounded --max-bars / --duration). Not a test, not a mock — a real executable
# path through the live Step 3.1-3.5 pipeline via the shared TradingCycle.
#
# Usage (from repo root, with a live Postgres reachable at DATABASE_URL, and a
# separate `python scripts/run_ingestion.py` feeding fresh bars):
#   DATABASE_URL=postgresql+asyncpg://... python scripts/run_paper_session.py \
#       [--symbol BTC/USDT] [--exchange binance] [--interval 1h] \
#       [--short-window 5] [--long-window 20] [--initial-capital 100000] \
#       [--max-position-pct 0.10] [--poll-seconds 15] \
#       [--max-bars N] [--duration-seconds S]
from __future__ import annotations

import argparse
import asyncio
import signal
import sys
from decimal import Decimal
from pathlib import Path
from uuid import UUID

# backend/ is a separate, unpackaged src-layout project (Doc 04) — bootstrap it
# onto sys.path rather than requiring callers to set PYTHONPATH themselves.
_BACKEND_SRC = Path(__file__).resolve().parent.parent / "backend" / "src"
sys.path.insert(0, str(_BACKEND_SRC))

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from quant_hub.application.execution.order_generation_service import OrderGenerationService  # noqa: E402
from quant_hub.application.execution.service import ExecutionService  # noqa: E402
from quant_hub.application.paper_trading.runner import (  # noqa: E402
    PaperCycleContext,
    PaperTradingRunner,
)
from quant_hub.application.portfolio.reference_constructors.weighted_sum import (  # noqa: E402
    WeightedSumConstructor,
)
from quant_hub.application.portfolio.reference_sizers.linear_conviction import (  # noqa: E402
    LinearConvictionSizer,
)
from quant_hub.application.strategy_engine.reference_strategies.moving_average_crossover import (  # noqa: E402
    MovingAverageCrossoverStrategy,
)
from quant_hub.application.strategy_engine.signal_recording_service import (  # noqa: E402
    SignalRecordingService,
)
from quant_hub.application.trading.cycle import TradingCycle  # noqa: E402
from quant_hub.api.dependencies import build_risk_gate  # noqa: E402
from quant_hub.domain.market_data.entities import AssetRef  # noqa: E402
from quant_hub.domain.portfolio.sizing import SizingConstraints  # noqa: E402
from quant_hub.domain.strategy_engine.entities import StrategyRef  # noqa: E402
from quant_hub.infrastructure.database import AsyncSessionLocal, engine  # noqa: E402
from quant_hub.infrastructure.strategy_engine.market_data_view import (  # noqa: E402
    RepositoryBackedMarketDataView,
)
from quant_hub.persistence.repositories.execution import (  # noqa: E402
    SQLAlchemyExecutionRepository,
    SQLAlchemyOrderRepository,
)
from quant_hub.persistence.repositories.market_data import (  # noqa: E402
    SQLAlchemyAssetRepository,
    SQLAlchemyOHLCVRepository,
    SQLAlchemyTickRepository,
)
from quant_hub.persistence.repositories.paper_trading import (  # noqa: E402
    SQLAlchemyPaperTradingSessionRepository,
)
from quant_hub.persistence.repositories.portfolio import SQLAlchemyPositionRepository  # noqa: E402
from quant_hub.persistence.repositories.strategy_engine import (  # noqa: E402
    SQLAlchemySignalRepository,
    SQLAlchemyStrategyRepository,
)

_STRATEGY_NAME = "reference-ma-crossover"


def _wire(session: AsyncSession) -> PaperCycleContext:
    """Composition root: assemble the shared TradingCycle over the REAL
    live-path collaborators for one unit of work (§10.5.4 — the same
    SignalRecordingService / Construction / Sizing / OrderGenerationService /
    ExecutionService + mandatory risk gate that run live). The strategy plugin
    is instantiated directly (the plugin under test); build_risk_gate is the
    fail-safe production gate (api/dependencies.py — real RiskApprovalAdapter,
    never the stub). Every repository is bound to `session`; nothing here
    commits (the runner owns the per-bar transaction boundary)."""
    assets = SQLAlchemyAssetRepository(session)
    bars = SQLAlchemyOHLCVRepository(session)
    ticks = SQLAlchemyTickRepository(session)
    positions = SQLAlchemyPositionRepository(session)
    orders = SQLAlchemyOrderRepository(session)
    executions = SQLAlchemyExecutionRepository(session)

    cycle = TradingCycle(
        strategy=MovingAverageCrossoverStrategy(),
        signal_recorder=SignalRecordingService(SQLAlchemySignalRepository(session)),
        sizer=LinearConvictionSizer(),
        constructor=WeightedSumConstructor(),
        order_gen=OrderGenerationService(orders, assets),
        execution=ExecutionService(orders, executions, positions, build_risk_gate(session)),
        positions=positions,
    )
    return PaperCycleContext(
        cycle=cycle,
        sessions=SQLAlchemyPaperTradingSessionRepository(session),
        bars=bars,
        assets=assets,
        positions=positions,
        view=RepositoryBackedMarketDataView(assets, bars, ticks),
    )


async def _ensure_paper_portfolio(session: AsyncSession, name: str) -> UUID:
    """Resolve-or-create the PAPER portfolio the session's trades land in.

    JUDGMENT CALL / FLAGGED TENSION (Doc 00 §14.5/§14.7; Doc 04 "no business
    logic in scripts/"): PortfolioRepository has no create() method and a
    governed portfolio-management service does not yet exist, so this bootstrap
    resolve-or-insert lives here — the minimal setup needed to have a
    portfolio_type='PAPER' portfolio for T-3 parity (paper trades reuse core.*
    tagged PAPER, per domain/paper_trading/interfaces.py). It is bootstrap
    wiring, analogous to run_reference_strategy.py's register_plugin, not trade
    logic; the proper home is a portfolio service/repo method (deferred, out of
    Step 5.2 scope). Idempotent on (name, portfolio_type='PAPER')."""
    row = (
        await session.execute(
            text(
                "SELECT id FROM core.portfolios "
                "WHERE name = :name AND portfolio_type = 'PAPER' AND deleted_at IS NULL"
            ),
            {"name": name},
        )
    ).scalar_one_or_none()
    if row is not None:
        return row
    created = (
        await session.execute(
            text(
                "INSERT INTO core.portfolios (name, description, base_currency, "
                "portfolio_type, is_active) "
                "VALUES (:name, :description, 'USD', 'PAPER', TRUE) RETURNING id"
            ),
            {"name": name, "description": "Paper trading portfolio (Step 5.2)"},
        )
    ).scalar_one()
    return created


async def _bootstrap(
    symbol: str, exchange: str, interval: str, short_window: int, long_window: int,
    initial_capital: Decimal,
) -> tuple[UUID, UUID, UUID, dict]:
    """Register the strategy, ensure the PAPER portfolio, and open the RUNNING
    session record — all in one committed unit of work. Returns
    (session_id, strategy_id, portfolio_id, strategy_config)."""
    strategy_config = {
        "symbol": symbol,
        "exchange": exchange,
        "asset_class": "crypto",
        "interval": interval,
        "short_window": short_window,
        "long_window": long_window,
    }
    async with AsyncSessionLocal() as session:
        portfolio_id = await _ensure_paper_portfolio(session, f"paper-{symbol.replace('/', '')}")
        strategy_id = await SQLAlchemyStrategyRepository(session).upsert(
            StrategyRef(
                name=_STRATEGY_NAME,
                version="1.0.0",
                description=(
                    "Trivial textbook MA-crossover reference plugin — proves the "
                    "paper pipeline end-to-end, not a real strategy"
                ),
                config=strategy_config,
                portfolio_id=portfolio_id,
            )
        )
        session_id = await SQLAlchemyPaperTradingSessionRepository(session).create(
            strategy_id=strategy_id,
            portfolio_id=portfolio_id,
            name=f"paper {symbol}@{exchange} {interval}",
            config=strategy_config,
            initial_capital=initial_capital,
            description="Step 5.2 continuous paper trading session",
        )
        await session.commit()
    return session_id, strategy_id, portfolio_id, strategy_config


async def run(args: argparse.Namespace) -> None:
    initial_capital = Decimal(str(args.initial_capital))
    session_id, strategy_id, portfolio_id, strategy_config = await _bootstrap(
        args.symbol, args.exchange, args.interval,
        args.short_window, args.long_window, initial_capital,
    )
    print(f"session started: id={session_id} strategy_id={strategy_id} portfolio_id={portfolio_id}")
    print(f"config: {strategy_config} initial_capital={initial_capital}")

    # Graceful stop: SIGINT/SIGTERM set an asyncio.Event so the runner closes
    # the session (STOPPED + ended_at) rather than dying mid-bar. Windows'
    # ProactorEventLoop does not support loop.add_signal_handler; there Ctrl-C
    # still arrives as KeyboardInterrupt, which the runner also treats as a
    # graceful stop. --duration-seconds is a bounded, non-interactive stop.
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, getattr(signal, "SIGTERM", signal.SIGINT)):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except (NotImplementedError, RuntimeError, ValueError):
            pass  # unsupported on this platform — fall back to KeyboardInterrupt
    if args.duration_seconds is not None:
        loop.call_later(args.duration_seconds, stop_event.set)

    runner = PaperTradingRunner(
        session_factory=AsyncSessionLocal,
        wire=_wire,
        poll_interval_seconds=args.poll_seconds,
    )
    asset = AssetRef(symbol=args.symbol, exchange=args.exchange, asset_class="crypto")
    try:
        summary = await runner.run(
            session_id=session_id,
            strategy_id=strategy_id,
            portfolio_id=portfolio_id,
            asset=asset,
            interval=args.interval,
            portfolio_value=initial_capital,
            strategy_config=strategy_config,
            constraints=SizingConstraints(max_position_pct=Decimal(str(args.max_position_pct))),
            max_bars=args.max_bars,
            stop_event=stop_event,
        )
    finally:
        await engine.dispose()

    print(
        f"session stopped: id={summary.session_id} reason={summary.stop_reason} "
        f"bars_processed={summary.bars_processed} signals={summary.signals_generated} "
        f"orders_created={summary.orders_created} filled={summary.orders_filled} "
        f"rejected={summary.orders_rejected} last_bar_ts={summary.last_bar_ts}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a continuous paper trading session (Step 5.2).")
    parser.add_argument("--symbol", default="BTC/USDT")
    parser.add_argument("--exchange", default="binance")
    parser.add_argument("--interval", default="1h")
    parser.add_argument("--short-window", type=int, default=5)
    parser.add_argument("--long-window", type=int, default=20)
    parser.add_argument("--initial-capital", default="100000")
    parser.add_argument("--max-position-pct", default="0.10")
    parser.add_argument("--poll-seconds", type=float, default=15.0)
    parser.add_argument(
        "--max-bars", type=int, default=None,
        help="stop after processing this many new bars (default: run until stopped)",
    )
    parser.add_argument(
        "--duration-seconds", type=float, default=None,
        help="stop after this many wall-clock seconds (default: run until stopped)",
    )
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()

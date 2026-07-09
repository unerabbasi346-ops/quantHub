#!/usr/bin/env python
"""Backtest the funding-carry strategy through QuantHub's Step 3.7 MTM engine.

Doc 14 §10.3 — deterministic historical replay through the real BacktestEngine, now
with point-in-time funding wired in (the additive PointInTimeMarketDataView.funding /
BacktestEngine.funding extension). Doc 04: automation only. Per Doc 00 §14.11.

HONESTY CAVEAT (critical — read before trusting the return number): QuantHub's trade
cycle marks POSITIONS to market (price P&L) but applies NO funding cashflow to P&L —
funding is modelled as market data (market_data.funding_rates), not yet a settled
financing cost on the position (Doc 14 §10.9.5 is not wired into Step 3.5). So this
backtest measures the PRICE P&L of the positions the funding-carry signal takes, and
NOT the funding income those positions exist to harvest. For a funding-CARRY strategy
that income is the entire point, so the Step 3.7 number below is necessary but NOT
sufficient. The funding-income diagnostic at the end estimates the missing piece
directly from the real funding series.
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

_BACKEND_SRC = Path(__file__).resolve().parent.parent / "backend" / "src"
sys.path.insert(0, str(_BACKEND_SRC))

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from quant_hub.api.dependencies import build_risk_gate  # noqa: E402
from quant_hub.application.backtesting.engine import BacktestEngine  # noqa: E402
from quant_hub.application.execution.order_generation_service import OrderGenerationService  # noqa: E402
from quant_hub.application.execution.service import ExecutionService  # noqa: E402
from quant_hub.application.portfolio.reference_constructors.weighted_sum import WeightedSumConstructor  # noqa: E402
from quant_hub.application.portfolio.reference_sizers.linear_conviction import LinearConvictionSizer  # noqa: E402
from quant_hub.application.strategy_engine.reference_strategies.funding_rate_basis import FundingRateBasisStrategy  # noqa: E402
from quant_hub.application.strategy_engine.signal_recording_service import SignalRecordingService  # noqa: E402
from quant_hub.domain.backtesting.entities import BacktestConfig  # noqa: E402
from quant_hub.domain.strategy_engine.entities import StrategyRef  # noqa: E402
from quant_hub.infrastructure.database import engine  # noqa: E402
from quant_hub.persistence.repositories.backtesting import SQLAlchemyBacktestRepository  # noqa: E402
from quant_hub.persistence.repositories.execution import (  # noqa: E402
    SQLAlchemyExecutionRepository,
    SQLAlchemyOrderRepository,
)
from quant_hub.persistence.repositories.market_data import (  # noqa: E402
    SQLAlchemyAssetRepository,
    SQLAlchemyFundingRateRepository,
    SQLAlchemyOHLCVRepository,
)
from quant_hub.persistence.repositories.portfolio import SQLAlchemyPositionRepository  # noqa: E402
from quant_hub.persistence.repositories.strategy_engine import (  # noqa: E402
    SQLAlchemySignalRepository,
    SQLAlchemyStrategyRepository,
)

_NAME = "reference-funding-basis"
_SYMBOL = "BTC/USDT:USDT"
_START = datetime(2026, 1, 25, tzinfo=timezone.utc)  # just after first funding row
_END = datetime(2026, 7, 10, tzinfo=timezone.utc)
_CAPITAL = Decimal("100000")


async def _fresh_portfolio(session: AsyncSession) -> UUID:
    row = await session.execute(
        text(
            "INSERT INTO core.portfolios (name, description, base_currency, portfolio_type, is_active) "
            "VALUES (:n, :d, 'USD', 'BACKTEST', TRUE) RETURNING id"
        ),
        {"n": f"bt-funding-{uuid4().hex[:8]}", "d": "Funding-carry backtest"},
    )
    return row.scalar_one()


async def _funding_income_diagnostic(session: AsyncSession) -> None:
    """Estimate the carry the STRATEGY would harvest — the piece Step 3.7 omits.

    The strategy leans SHORT when funding is positive (collect) and LONG when negative.
    A perfectly-aligned carry position collects |funding_rate| every period, so
    sum(|funding_rate|) over the window is the gross carry per unit notional if the
    sign is always right; sum(funding_rate) is the carry of a constant-SHORT position.
    Both are reported so the number is not spun."""
    rows = (await session.execute(text(
        "SELECT f.funding_rate FROM market_data.funding_rates f "
        "JOIN market_data.assets a ON a.id = f.asset_id "
        "WHERE a.symbol = :s AND f.funding_time >= :start AND f.funding_time < :end "
        "ORDER BY f.funding_time"
    ), {"s": _SYMBOL, "start": _START, "end": _END})).scalars().all()
    rates = [float(r) for r in rows]
    if not rates:
        print("  (no funding rows in window)")
        return
    n = len(rates)
    pos = sum(1 for r in rates if r > 0)
    sum_signed = sum(rates)          # carry of a constant-short position
    sum_abs = sum(abs(r) for r in rates)  # carry if always on the collecting side
    print(f"  funding periods (8h)      : {n}  ({pos} positive, {n - pos} negative)")
    print(f"  mean funding rate/period  : {sum(rates)/n:+.6%}")
    print(f"  sum funding (const-short) : {sum_signed:+.4%}  gross carry over window, per unit notional")
    print(f"  sum |funding|(always-right): {sum_abs:+.4%}  upper bound if sign always correct")
    print("  NOTE: these are per-unit-NOTIONAL carries; actual $ carry = above x notional")
    print("        held, and the reference sizer holds only ~value x 0.05 x capital.")


async def run() -> None:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        strategy_id = await SQLAlchemyStrategyRepository(session).upsert(
            StrategyRef(name=_NAME, version="1.0.0",
                        description="Funding-carry reference — OOS backtest",
                        config={"symbol": _SYMBOL, "exchange": "binance"})
        )
        portfolio_id = await _fresh_portfolio(session)
        await session.commit()

    print(f"Funding-carry backtest (Step 3.7 MTM) — {_SYMBOL}  {_START.date()} -> {_END.date()}\n")

    async with AsyncSession(engine, expire_on_commit=False) as session:
        assets = SQLAlchemyAssetRepository(session)
        bars = SQLAlchemyOHLCVRepository(session)
        positions = SQLAlchemyPositionRepository(session)
        orders = SQLAlchemyOrderRepository(session)
        executions = SQLAlchemyExecutionRepository(session)
        eng = BacktestEngine(
            bars=bars, assets=assets, positions=positions,
            backtests=SQLAlchemyBacktestRepository(session),
            signal_recorder=SignalRecordingService(SQLAlchemySignalRepository(session)),
            sizer=LinearConvictionSizer(), constructor=WeightedSumConstructor(),
            order_gen=OrderGenerationService(orders, assets),
            execution=ExecutionService(orders, executions, positions, build_risk_gate(session)),
            strategy_plugin=FundingRateBasisStrategy(),
            funding=SQLAlchemyFundingRateRepository(session),  # the additive point-in-time funding wiring
        )
        cfg = BacktestConfig(
            name="funding-carry-oos", symbol=_SYMBOL, exchange="binance", asset_class="crypto",
            interval="1d",
            strategy_config={"symbol": _SYMBOL, "exchange": "binance", "asset_class": "crypto",
                             "window": 3, "scale": 1000},
            start=_START, end=_END, initial_capital=_CAPITAL, max_position_pct=Decimal("0.20"),
        )
        _, res = await eng.run(cfg, strategy_id=strategy_id, portfolio_id=portfolio_id)
        await session.commit()

    print("STEP 3.7 RESULT (price P&L only — see caveat):")
    print(f"  bars processed     : {res.bars_processed}")
    print(f"  signals generated  : {res.signals_generated}")
    print(f"  orders filled      : {res.orders_filled}")
    print(f"  final position qty : {res.final_position_quantity}")
    print(f"  realized PnL       : {float(res.realized_pnl):+.2f}")
    print(f"  unrealized PnL     : {float(res.unrealized_pnl):+.2f}")
    print(f"  total return       : {float(res.total_return)*100:+.4f}%")
    print(f"  reproducibility    : {res.reproducibility_hash[:16]}...")

    print("\nFUNDING-INCOME DIAGNOSTIC (the piece Step 3.7 does NOT apply):")
    async with AsyncSession(engine, expire_on_commit=False) as session:
        await _funding_income_diagnostic(session)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())

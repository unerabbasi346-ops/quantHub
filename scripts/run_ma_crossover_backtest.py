#!/usr/bin/env python
"""Backtest the reference MA-crossover strategy through QuantHub's Step 3.7
MTM engine, mirroring scripts/run_funding_backtest.py's real-BacktestEngine
pattern for the platform's other ACTIVE reference strategy.

Doc 14 §10.3 target window: ~5 years (2020-01-01 -> 2025-01-01), now that
BTC/USDT 1h history has been backfilled that far back (previously only ~5
days existed, per the live-testing bug-fix pass, item 0).
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
from quant_hub.application.strategy_engine.reference_strategies.moving_average_crossover import (  # noqa: E402
    MovingAverageCrossoverStrategy,
)
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
    SQLAlchemyOHLCVRepository,
)
from quant_hub.persistence.repositories.portfolio import SQLAlchemyPositionRepository  # noqa: E402
from quant_hub.persistence.repositories.strategy_engine import (  # noqa: E402
    SQLAlchemySignalRepository,
    SQLAlchemyStrategyRepository,
)

_NAME = "reference-ma-crossover"
_SYMBOL = "BTC/USDT"
_START = datetime(2020, 1, 1, tzinfo=timezone.utc)  # Doc 14 §10.3 5yr target window
_END = datetime(2025, 1, 1, tzinfo=timezone.utc)
_CAPITAL = Decimal("100000")


async def _fresh_portfolio(session: AsyncSession) -> UUID:
    row = await session.execute(
        text(
            "INSERT INTO core.portfolios (name, description, base_currency, portfolio_type, is_active) "
            "VALUES (:n, :d, 'USD', 'BACKTEST', TRUE) RETURNING id"
        ),
        {"n": f"bt-ma-crossover-{uuid4().hex[:8]}", "d": "MA-crossover backtest"},
    )
    return row.scalar_one()


async def run() -> None:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        strategy_id = await SQLAlchemyStrategyRepository(session).upsert(
            StrategyRef(
                name=_NAME, version="1.0.0",
                description="Trivial textbook MA-crossover reference plugin — OOS backtest",
                config={
                    "symbol": _SYMBOL, "exchange": "binance", "asset_class": "crypto",
                    "interval": "1h", "short_window": 5, "long_window": 20,
                },
            )
        )
        portfolio_id = await _fresh_portfolio(session)
        await session.commit()

    print(f"MA-crossover backtest (Step 3.7 MTM) — {_SYMBOL}  {_START.date()} -> {_END.date()}\n")

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
            strategy_plugin=MovingAverageCrossoverStrategy(),
        )
        cfg = BacktestConfig(
            name="ma-crossover-oos", symbol=_SYMBOL, exchange="binance", asset_class="crypto",
            interval="1h",
            strategy_config={
                "symbol": _SYMBOL, "exchange": "binance", "asset_class": "crypto",
                "interval": "1h", "short_window": 5, "long_window": 20,
            },
            start=_START, end=_END, initial_capital=_CAPITAL, max_position_pct=Decimal("0.20"),
        )
        _, res = await eng.run(cfg, strategy_id=strategy_id, portfolio_id=portfolio_id)
        await session.commit()

    print("STEP 3.7 RESULT:")
    print(f"  bars processed     : {res.bars_processed}")
    print(f"  signals generated  : {res.signals_generated}")
    print(f"  orders filled      : {res.orders_filled}")
    print(f"  final position qty : {res.final_position_quantity}")
    print(f"  realized PnL       : {float(res.realized_pnl):+.2f}")
    print(f"  unrealized PnL     : {float(res.unrealized_pnl):+.2f}")
    print(f"  total return       : {float(res.total_return)*100:+.4f}%")
    print(f"  reproducibility    : {res.reproducibility_hash[:16]}...")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())

"""Run the TP/SL + one-trade + 2%/3%-sizing backtest engine across every
ACTIVE strategy x every same-instrument-type asset with enough 1h bars.

Mirrors scripts/run_ma_crossover_backtest.py's real-collaborator wiring
(no mocks — Doc 00 §14.5): real repositories, real order/execution path,
results persisted to analytics.backtests / backtest_equity_curve /
backtest_computed_metrics by the engine itself.

Strategies without a platform plugin class (e.g. lancaster-ml-momentum,
whose signals come from the external research pipeline) are reported and
skipped — replaying them here is impossible, not optional.

Run:  DATABASE_URL=... uv run --project backend python backend/scripts/run_all_backtests.py
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from quant_hub.api.dependencies import build_risk_gate
from quant_hub.application.backtesting.engine import BacktestEngine
from quant_hub.application.execution.order_generation_service import OrderGenerationService
from quant_hub.application.execution.service import ExecutionService
from quant_hub.application.portfolio.reference_constructors.weighted_sum import WeightedSumConstructor
from quant_hub.application.portfolio.reference_sizers.linear_conviction import LinearConvictionSizer
from quant_hub.application.strategy_engine.reference_strategies.funding_rate_basis import FundingRateBasisStrategy
from quant_hub.application.strategy_engine.reference_strategies.moving_average_crossover import (
    MovingAverageCrossoverStrategy,
)
from quant_hub.application.strategy_engine.signal_recording_service import SignalRecordingService
from quant_hub.domain.backtesting.entities import BacktestConfig
from quant_hub.infrastructure.database import AsyncSessionLocal, engine
from quant_hub.persistence.repositories.backtesting import SQLAlchemyBacktestRepository
from quant_hub.persistence.repositories.execution import (
    SQLAlchemyExecutionRepository,
    SQLAlchemyOrderRepository,
)
from quant_hub.persistence.repositories.market_data import (
    SQLAlchemyAssetRepository,
    SQLAlchemyFundingRateRepository,
    SQLAlchemyOHLCVRepository,
)
from quant_hub.persistence.repositories.portfolio import SQLAlchemyPositionRepository
from quant_hub.persistence.repositories.strategy_engine import (
    SQLAlchemySignalRepository,
    SQLAlchemyStrategyRepository,
)

INTERVAL = "1h"
MIN_BARS = 200
# ponytail: per-combo window capped at the most recent 5000 1h bars (~7 months)
# so a full sweep stays tractable; raise for a full-history sweep.
MAX_BARS = 5000
CAPITAL = Decimal("100000")

# name -> (plugin factory, instrument type it trades, needs funding data)
STRATEGY_PLUGINS = {
    "reference-ma-crossover": (MovingAverageCrossoverStrategy, "SPOT", False),
    "reference-funding-basis": (FundingRateBasisStrategy, "PERPETUAL", True),
}


async def _eligible_assets(session: AsyncSession, instrument_type: str) -> list[dict]:
    """Active assets of the given instrument type with >= MIN_BARS 1h bars,
    plus the ts window of their most recent MAX_BARS bars."""
    rows = await session.execute(
        text("""
            SELECT a.id, a.symbol, a.exchange, counted.n,
                   counted.win_start, counted.win_end
            FROM market_data.assets a
            JOIN LATERAL (
                SELECT count(*) AS n, min(w.ts) AS win_start, max(w.ts) AS win_end
                FROM (
                    SELECT ts FROM market_data.ohlcv_bars
                    WHERE asset_id = a.id AND interval = :interval
                    ORDER BY ts DESC LIMIT :max_bars
                ) w
            ) counted ON TRUE
            WHERE a.is_active AND a.instrument_type = :itype AND counted.n >= :min_bars
            ORDER BY a.symbol
        """),
        {"interval": INTERVAL, "itype": instrument_type, "min_bars": MIN_BARS, "max_bars": MAX_BARS},
    )
    return [
        {"id": r.id, "symbol": r.symbol, "exchange": r.exchange, "bars": r.n,
         "start": r.win_start, "end": r.win_end}
        for r in rows
    ]


async def _fresh_portfolio(session: AsyncSession, label: str) -> UUID:
    row = await session.execute(
        text(
            "INSERT INTO core.portfolios (name, description, base_currency, portfolio_type, is_active) "
            "VALUES (:n, :d, 'USD', 'BACKTEST', TRUE) RETURNING id"
        ),
        {"n": f"bt-{label}-{uuid4().hex[:8]}", "d": "run_all_backtests sweep"},
    )
    return row.scalar_one()


async def _run_one(
    strategy_row, plugin_cls, needs_funding: bool, asset: dict
) -> dict:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        portfolio_id = await _fresh_portfolio(session, strategy_row.name[:20])
        await session.commit()

        assets = SQLAlchemyAssetRepository(session)
        bars = SQLAlchemyOHLCVRepository(session)
        positions = SQLAlchemyPositionRepository(session)
        orders = SQLAlchemyOrderRepository(session)
        executions = SQLAlchemyExecutionRepository(session)
        backtests = SQLAlchemyBacktestRepository(session)

        strategy_config = dict(strategy_row.config)
        strategy_config.update({
            "symbol": asset["symbol"], "exchange": asset["exchange"],
            "asset_class": "crypto", "interval": INTERVAL,
        })

        eng = BacktestEngine(
            bars=bars, assets=assets, positions=positions, backtests=backtests,
            signal_recorder=SignalRecordingService(SQLAlchemySignalRepository(session)),
            sizer=LinearConvictionSizer(), constructor=WeightedSumConstructor(),
            order_gen=OrderGenerationService(orders, assets),
            execution=ExecutionService(orders, executions, positions, build_risk_gate(session)),
            strategy_plugin=plugin_cls(),
            funding=SQLAlchemyFundingRateRepository(session) if needs_funding else None,
        )
        cfg = BacktestConfig(
            name=f"sweep-{strategy_row.name}-{asset['symbol']}",
            symbol=asset["symbol"], exchange=asset["exchange"], asset_class="crypto",
            interval=INTERVAL, strategy_config=strategy_config,
            start=asset["start"], end=asset["end"],
            initial_capital=CAPITAL, max_position_pct=Decimal("0.20"),
        )
        backtest_id, res = await eng.run(cfg, strategy_id=strategy_row.id, portfolio_id=portfolio_id)
        await session.commit()

        metrics = await backtests.get_computed_metrics(backtest_id)

    return {
        "strategy": strategy_row.name,
        "symbol": asset["symbol"],
        "bars": res.bars_processed,
        "trades": res.trade_count,
        "return_pct": float(res.total_return) * 100,
        "benchmark_pct": float(res.benchmark_return) * 100 if res.benchmark_return is not None else None,
        "win_rate": _f(getattr(metrics, "win_rate", None)),
        "sharpe": _f(getattr(metrics, "sharpe_ratio", None)),
        "max_drawdown": _f(getattr(metrics, "max_drawdown_pct", None)),
    }


def _f(v) -> float | None:
    return None if v is None else float(v)


def _fmt(v, pct=False) -> str:
    if v is None:
        return "—"
    return f"{v * 100:+.2f}%" if pct else f"{v:+.2f}"


async def main() -> None:
    async with AsyncSessionLocal() as session:
        strategies = [
            s for s in await SQLAlchemyStrategyRepository(session).list_all()
            if s.status == "ACTIVE"
        ]

    results: list[dict] = []
    for strategy_row in strategies:
        entry = STRATEGY_PLUGINS.get(strategy_row.name)
        if entry is None:
            print(f"SKIP {strategy_row.name}: no platform plugin class (external/research strategy) — cannot replay.")
            continue
        plugin_cls, itype, needs_funding = entry

        async with AsyncSessionLocal() as session:
            assets = await _eligible_assets(session, itype)
        print(f"\n{strategy_row.name} ({itype}): {len(assets)} assets with >= {MIN_BARS} {INTERVAL} bars")

        for asset in assets:
            started = datetime.now()
            try:
                row = await _run_one(strategy_row, plugin_cls, needs_funding, asset)
            except Exception as exc:  # report and continue the sweep, never fabricate
                print(f"  FAILED {asset['symbol']}: {type(exc).__name__}: {exc}")
                continue
            secs = (datetime.now() - started).total_seconds()
            results.append(row)
            print(
                f"  {asset['symbol']:20s} bars={row['bars']:5d} trades={row['trades']:4d} "
                f"return={row['return_pct']:+7.3f}% bench={_fmt(row['benchmark_pct'] and row['benchmark_pct'] / 100, pct=True):>8s} "
                f"win={_fmt(row['win_rate'], pct=True):>8s} sharpe={_fmt(row['sharpe']):>7s} "
                f"maxDD={_fmt(row['max_drawdown'], pct=True):>8s} ({secs:.0f}s)"
            )

    print(f"\n{'=' * 60}\nAggregate: {len(results)} backtests completed")
    if results:
        rets = [r["return_pct"] for r in results]
        profitable = sum(1 for r in rets if r > 0)
        print(f"  profitable combos : {profitable}/{len(results)}")
        print(f"  mean return       : {sum(rets) / len(rets):+.3f}%")
        print(f"  best              : {max(results, key=lambda r: r['return_pct'])['strategy']} "
              f"{max(results, key=lambda r: r['return_pct'])['symbol']} {max(rets):+.3f}%")
        print(f"  worst             : {min(results, key=lambda r: r['return_pct'])['strategy']} "
              f"{min(results, key=lambda r: r['return_pct'])['symbol']} {min(rets):+.3f}%")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

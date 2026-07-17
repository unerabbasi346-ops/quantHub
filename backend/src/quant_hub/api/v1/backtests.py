# Governing specification: Doc 07 — Backend Architecture (§API Standards,
#   §Background Processing: backtests are long-running and run asynchronously).
# Doc 14 §10.3 Backtesting Engine — run/inspect surface over the REAL
#   BacktestEngine and the analytics.backtests / backtest_equity_curve /
#   backtest_computed_metrics rows it persists. Doc 00 §14.5/§14.7 DATA
#   HONESTY: everything served here is an engine-computed row, never derived
#   client-side and never fabricated.
#
# Research-page vertical slice: the cross-strategy backtest explorer needs a
# list of ALL runs (the per-strategy feed under /strategies/{id}/backtests
# can't see across strategies), the equity curve for charting, and a way to
# START a run. Runs execute via FastAPI BackgroundTasks — same flagged
# judgment call as api/ml.py (blocks the event loop while replaying; no new
# queue/worker introduced).
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Query, status
from pydantic import BaseModel, field_serializer
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from quant_hub.api.dependencies import DbSession, StrategyRepo, build_risk_gate
from quant_hub.api.envelope import ApiError, ErrorCode, ResponseEnvelope, ok
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
from quant_hub.infrastructure.database import engine as db_engine
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

router = APIRouter(tags=["backtests"])

# Only strategies with a platform plugin class are replayable — external/
# research strategies (e.g. lancaster-ml-momentum) record signals through
# their own pipeline and cannot be re-run here. Honest 400, never a fake run.
_RUNNABLE_PLUGINS = {
    "reference-ma-crossover": (MovingAverageCrossoverStrategy, False),
    "reference-funding-basis": (FundingRateBasisStrategy, True),  # needs funding data
}


class BacktestSummaryOut(BaseModel):
    """One analytics.backtests row joined with its computed metric suite —
    the cross-strategy explorer row. Metric fields are null when the run has
    no computed metrics yet (RUNNING, or a legacy row) — never fabricated."""

    id: UUID
    strategy_id: UUID | None
    strategy_name: str | None
    name: str
    symbol: str | None
    status: str
    start_date: date | None
    end_date: date | None
    total_return: Decimal | None
    benchmark_return: Decimal | None
    trade_count: int | None
    win_rate: Decimal | None
    sharpe_ratio: Decimal | None
    sortino_ratio: Decimal | None
    max_drawdown_pct: Decimal | None
    profit_factor: Decimal | None
    initial_capital: Decimal | None
    final_capital: Decimal | None
    created_at: datetime

    @field_serializer(
        "total_return", "benchmark_return", "win_rate", "sharpe_ratio", "sortino_ratio",
        "max_drawdown_pct", "profit_factor", "initial_capital", "final_capital",
        when_used="json",
    )
    def _serialize_decimal(self, value: Decimal | None) -> str | None:
        return None if value is None else format(value, "f")


@router.get(
    "/backtests",
    response_model=ResponseEnvelope[list[BacktestSummaryOut]],
    summary="List all backtest runs across strategies, with computed metrics",
)
async def list_backtests(
    session: DbSession,
    limit: int = Query(100, ge=1, le=500),
) -> ResponseEnvelope[list[BacktestSummaryOut]]:
    result = await session.execute(
        sa_text(
            """
            SELECT b.id, b.strategy_id, s.name AS strategy_name, b.name,
                   b.config->>'symbol' AS symbol, b.status,
                   b.start_date, b.end_date, b.total_return, b.benchmark_return,
                   b.trade_count, b.initial_capital, b.final_capital, b.created_at,
                   m.win_rate, m.sharpe_ratio, m.sortino_ratio, m.max_drawdown_pct,
                   m.profit_factor
            FROM analytics.backtests b
            LEFT JOIN core.strategies s ON s.id = b.strategy_id
            LEFT JOIN analytics.backtest_computed_metrics m ON m.backtest_run_id = b.id
            ORDER BY b.created_at DESC
            LIMIT :limit
            """
        ),
        {"limit": limit},
    )
    return ok([BacktestSummaryOut.model_validate(dict(row)) for row in result.mappings()])


class EquityPointOut(BaseModel):
    ts: datetime
    portfolio_value: Decimal
    return_pct: Decimal

    @field_serializer("portfolio_value", "return_pct", when_used="json")
    def _serialize_decimal(self, value: Decimal) -> str:
        return format(value, "f")


@router.get(
    "/backtests/{backtest_id}/equity-curve",
    response_model=ResponseEnvelope[list[EquityPointOut]],
    summary="Get a backtest's persisted per-step equity curve (downsampled)",
)
async def get_equity_curve(
    backtest_id: UUID,
    session: DbSession,
    max_points: int = Query(500, ge=10, le=5000),
) -> ResponseEnvelope[list[EquityPointOut]]:
    """Real persisted curve points; evenly stride-downsampled server-side
    (every Nth REAL point, always including the last) so a 5000-bar run
    doesn't ship 5000 rows to the chart. No interpolation — every point
    returned is an actual engine-computed equity mark."""
    count_row = await session.execute(
        sa_text(
            "SELECT count(*) FROM analytics.backtest_equity_curve WHERE backtest_run_id = :id"
        ),
        {"id": backtest_id},
    )
    total = count_row.scalar_one()
    if total == 0:
        raise ApiError(
            status.HTTP_404_NOT_FOUND,
            ErrorCode.RESOURCE_NOT_FOUND,
            f"No equity curve stored for backtest {backtest_id}",
        )
    stride = max(1, total // max_points)
    result = await session.execute(
        sa_text(
            """
            SELECT ts, portfolio_value, return_pct
            FROM analytics.backtest_equity_curve
            WHERE backtest_run_id = :id AND (step % :stride = 0 OR step = :last)
            ORDER BY step
            """
        ),
        {"id": backtest_id, "stride": stride, "last": total - 1},
    )
    return ok([EquityPointOut.model_validate(dict(row)) for row in result.mappings()])


class RunBacktestRequest(BaseModel):
    strategy_id: UUID
    symbol: str
    exchange: str = "binance"
    start: datetime
    end: datetime
    initial_capital: Decimal = Decimal("100000")


class RunBacktestOut(BaseModel):
    run_name: str
    status: str  # "STARTED"
    note: str


async def _run_backtest_job(
    *, run_name: str, strategy_id: UUID, strategy_name: str, strategy_config: dict[str, Any],
    symbol: str, exchange: str, start: datetime, end: datetime, initial_capital: Decimal,
) -> None:
    """Background replay — opens its own session (the request's is closed by
    now), same convention as api/ml.py's training job. The engine itself
    creates and completes the analytics.backtests row, so failure before
    `create` leaves nothing behind and failure after leaves an honest
    non-COMPLETED row."""
    plugin_cls, needs_funding = _RUNNABLE_PLUGINS[strategy_name]
    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        row = await session.execute(
            sa_text(
                "INSERT INTO core.portfolios (name, description, base_currency, portfolio_type, is_active) "
                "VALUES (:n, 'research-page backtest run', 'USD', 'BACKTEST', TRUE) RETURNING id"
            ),
            {"n": f"bt-api-{uuid4().hex[:8]}"},
        )
        portfolio_id = row.scalar_one()
        await session.commit()

        assets = SQLAlchemyAssetRepository(session)
        orders = SQLAlchemyOrderRepository(session)
        engine = BacktestEngine(
            bars=SQLAlchemyOHLCVRepository(session),
            assets=assets,
            positions=SQLAlchemyPositionRepository(session),
            backtests=SQLAlchemyBacktestRepository(session),
            signal_recorder=SignalRecordingService(SQLAlchemySignalRepository(session)),
            sizer=LinearConvictionSizer(),
            constructor=WeightedSumConstructor(),
            order_gen=OrderGenerationService(orders, assets),
            execution=ExecutionService(
                orders, SQLAlchemyExecutionRepository(session),
                SQLAlchemyPositionRepository(session), build_risk_gate(session),
            ),
            strategy_plugin=plugin_cls(),
            funding=SQLAlchemyFundingRateRepository(session) if needs_funding else None,
        )
        config = BacktestConfig(
            name=run_name, symbol=symbol, exchange=exchange, asset_class="crypto",
            interval=str(strategy_config.get("interval", "1h")),
            strategy_config={**strategy_config, "symbol": symbol, "exchange": exchange},
            start=start, end=end, initial_capital=initial_capital,
            max_position_pct=Decimal("0.20"),
        )
        await engine.run(config, strategy_id=strategy_id, portfolio_id=portfolio_id)
        await session.commit()


@router.post(
    "/backtests",
    response_model=ResponseEnvelope[RunBacktestOut],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start a backtest run in the background (plugin strategies only)",
)
async def run_backtest(
    body: RunBacktestRequest,
    background_tasks: BackgroundTasks,
    strategy_repo: StrategyRepo,
    session: DbSession,
) -> ResponseEnvelope[RunBacktestOut]:
    strategy = await strategy_repo.get_by_id(body.strategy_id)
    if strategy is None:
        raise ApiError(
            status.HTTP_404_NOT_FOUND,
            ErrorCode.RESOURCE_NOT_FOUND,
            f"Strategy {body.strategy_id} not found",
        )
    if strategy.name not in _RUNNABLE_PLUGINS:
        raise ApiError(
            status.HTTP_400_BAD_REQUEST,
            ErrorCode.VALIDATION_ERROR,
            f"Strategy {strategy.name!r} has no platform plugin class and cannot be replayed "
            f"(runnable: {sorted(_RUNNABLE_PLUGINS)})",
        )
    if body.end <= body.start:
        raise ApiError(
            status.HTTP_400_BAD_REQUEST, ErrorCode.VALIDATION_ERROR, "end must be after start"
        )
    asset_id = await SQLAlchemyAssetRepository(session).get_by_symbol_exchange(body.symbol, body.exchange)
    if asset_id is None:
        raise ApiError(
            status.HTTP_400_BAD_REQUEST,
            ErrorCode.VALIDATION_ERROR,
            f"No ingested data for {body.symbol}@{body.exchange}",
        )

    run_name = f"research-{strategy.name}-{body.symbol}-{datetime.now(timezone.utc):%Y%m%d%H%M%S}"
    background_tasks.add_task(
        _run_backtest_job,
        run_name=run_name, strategy_id=strategy.id, strategy_name=strategy.name,
        strategy_config=dict(strategy.config), symbol=body.symbol, exchange=body.exchange,
        start=body.start, end=body.end, initial_capital=body.initial_capital,
    )
    return ok(RunBacktestOut(
        run_name=run_name,
        status="STARTED",
        note="Poll GET /v1/backtests until this run_name shows status COMPLETED.",
    ))

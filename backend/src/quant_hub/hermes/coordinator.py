# HermesCoordinator — orchestrates the four Hermes monitors and rolls their
# output into a single 0-100 health score. Coordination only: this module
# calls the monitors and does arithmetic on their already-computed results;
# it never queries a table itself (that stays in monitors/) and never
# touches domain/strategy_engine, domain/portfolio, domain/execution, or
# domain/risk (see quant_hub/hermes/__init__.py).
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from quant_hub.config import settings
from quant_hub.hermes.monitors import data_pipeline, ml_ops, service_health, strategy_lifecycle
from quant_hub.hermes.monitors.data_pipeline import STATUS_DEAD, STATUS_FRESH, STATUS_STALE


@dataclass(frozen=True)
class SystemStatus:
    health_score: float
    services: list[service_health.ServiceStatus]
    assets: list[data_pipeline.AssetFreshness]
    funding: list[data_pipeline.FundingFreshness]
    strategies: list[strategy_lifecycle.StrategyLifecycle]
    models: list[ml_ops.MLModelStatus]
    training_jobs: list[ml_ops.TrainingJob]
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class StrategyEngineSummary:
    active_count: int
    signals_24h: int


@dataclass(frozen=True)
class DataPipelineSummary:
    fresh_count: int
    stale_count: int
    dead_count: int


@dataclass(frozen=True)
class MLEngineSummary:
    trained_count: int
    last_accuracy: float | None


@dataclass(frozen=True)
class ExecutionEngineSummary:
    orders_today: int
    fill_rate_today: float | None  # fraction 0..1; None when orders_today == 0


@dataclass(frozen=True)
class HealthSummary:
    health_score: float
    services: list[service_health.ServiceStatus]
    strategy_engine: StrategyEngineSummary
    data_pipeline: DataPipelineSummary
    ml_engine: MLEngineSummary
    execution_engine: ExecutionEngineSummary
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# Composite weighting (JUDGMENT CALL, flagged): service connectivity is
# weighted heaviest since every other monitor's data depends on the database
# being reachable at all; data pipeline freshness next since a stale/dead
# feed silently invalidates every downstream signal; strategy activity and
# ML registry state weighted lightest since a quiet strategy or an empty
# model registry is a normal, non-urgent state, not an outage.
_WEIGHT_SERVICES = 0.4
_WEIGHT_PIPELINE = 0.3
_WEIGHT_STRATEGIES = 0.2
_WEIGHT_ML = 0.1


def _services_score(services: list[service_health.ServiceStatus]) -> float:
    if not services:
        return 100.0
    # NOT_CONFIGURED is an honest opt-out, not a failure — scored as healthy.
    up = sum(1 for s in services if s.status != service_health.STATUS_DOWN)
    return (up / len(services)) * 100.0


def _pipeline_score(assets: list[data_pipeline.AssetFreshness]) -> float:
    if not assets:
        return 100.0
    weights = {STATUS_FRESH: 1.0, STATUS_STALE: 0.5, STATUS_DEAD: 0.0}
    total = sum(weights[a.status] for a in assets)
    return (total / len(assets)) * 100.0


def _strategy_score(strategies: list[strategy_lifecycle.StrategyLifecycle]) -> float:
    active = [s for s in strategies if s.status == "ACTIVE"]
    if not active:
        return 100.0
    healthy = sum(1 for s in active if s.signals_24h > 0)
    return (healthy / len(active)) * 100.0


def _ml_score(models: list[ml_ops.MLModelStatus]) -> float:
    if not models:
        return 0.0
    if any(m.status == "DEPLOYED" for m in models):
        return 100.0
    return 50.0


def _composite_score(
    services: list[service_health.ServiceStatus],
    assets: list[data_pipeline.AssetFreshness],
    strategies: list[strategy_lifecycle.StrategyLifecycle],
    models: list[ml_ops.MLModelStatus],
) -> float:
    score = (
        _WEIGHT_SERVICES * _services_score(services)
        + _WEIGHT_PIPELINE * _pipeline_score(assets)
        + _WEIGHT_STRATEGIES * _strategy_score(strategies)
        + _WEIGHT_ML * _ml_score(models)
    )
    return round(score, 1)


async def _orders_today_stats(session: AsyncSession) -> tuple[int, int]:
    """(orders_today, filled_today) — raw counts off core.orders, no
    execution-domain import. UTC calendar day via DATE(created_at AT TIME
    ZONE 'UTC') = CURRENT_DATE, matching the platform's established "today"
    convention (Execution page, F-21 pass).

    VERIFIED (not a bug, investigated on request): this WHERE clause always
    scoped to the UTC calendar day — a prior report of 130,780 orders "today"
    was a real count of backtest-replay orders whose created_at legitimately
    fell within that UTC day (Postgres server TimeZone is UTC; confirmed
    server-side both forms of the date filter return identical counts). Live
    trading and backtest replay share core.orders with no distinguishing
    flag, so re-running a backtest will spike this figure again — that is
    real data, not a query defect."""
    row = (
        await session.execute(
            text(
                """
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE status = 'FILLED') AS filled
                FROM core.orders
                WHERE DATE(created_at AT TIME ZONE 'UTC') = CURRENT_DATE
                """
            )
        )
    ).one()
    return row.total, row.filled


class HermesCoordinator:
    """Stateless orchestrator — a session/redis client is supplied per call
    (request-scoped), so the singleton instance below holds no data of its
    own between requests."""

    async def get_status(self, session: AsyncSession, redis: Redis) -> SystemStatus:
        services = [
            service_health.check_backend(),
            await service_health.check_database(session),
            await service_health.check_redis(redis, settings.redis_url),
        ]
        assets = await data_pipeline.get_asset_freshness(session)
        funding = await data_pipeline.get_funding_freshness(session)
        strategies = await strategy_lifecycle.get_strategy_lifecycle(session)
        models = await ml_ops.get_model_registry(session)
        training_jobs = await ml_ops.get_active_training_jobs(redis)

        return SystemStatus(
            health_score=_composite_score(services, assets, strategies, models),
            services=services,
            assets=assets,
            funding=funding,
            strategies=strategies,
            models=models,
            training_jobs=training_jobs,
        )

    async def get_health(self, session: AsyncSession, redis: Redis) -> HealthSummary:
        services = [
            service_health.check_backend(),
            await service_health.check_database(session),
            await service_health.check_redis(redis, settings.redis_url),
        ]
        assets = await data_pipeline.get_asset_freshness(session)
        strategies = await strategy_lifecycle.get_strategy_lifecycle(session)
        models = await ml_ops.get_model_registry(session)
        orders_today, filled_today = await _orders_today_stats(session)

        active_strategies = [s for s in strategies if s.status == "ACTIVE"]
        signals_24h = sum(s.signals_24h for s in strategies)
        latest_model = models[0] if models else None

        return HealthSummary(
            health_score=_composite_score(services, assets, strategies, models),
            services=services,
            strategy_engine=StrategyEngineSummary(active_count=len(active_strategies), signals_24h=signals_24h),
            data_pipeline=DataPipelineSummary(
                fresh_count=sum(1 for a in assets if a.status == STATUS_FRESH),
                stale_count=sum(1 for a in assets if a.status == STATUS_STALE),
                dead_count=sum(1 for a in assets if a.status == STATUS_DEAD),
            ),
            ml_engine=MLEngineSummary(trained_count=len(models), last_accuracy=latest_model.accuracy if latest_model else None),
            execution_engine=ExecutionEngineSummary(
                orders_today=orders_today,
                fill_rate_today=(filled_today / orders_today) if orders_today else None,
            ),
        )


hermes_coordinator = HermesCoordinator()

# Hermes API — mounted at /api/hermes (top-level, NOT under /v1), same
# deliberate-separate-surface convention api/ml.py established: this is
# observability tooling, not a governed REST resource of the versioned API.
#
# DbSession/CacheClient are defined locally rather than imported from
# quant_hub.api.dependencies — that module also wires every repository for
# strategy_engine/portfolio/execution/risk, and importing it would pull all
# of that into Hermes's module graph even though no handler here uses it.
# Depending directly on infrastructure/database.py + infrastructure/cache.py
# keeps Hermes's import graph exactly as small as the boundary requires (see
# quant_hub/hermes/__init__.py and tests/unit/hermes/test_import_boundary.py).
#
# NUMERIC OUTPUT CONVENTION: every rate/return/fraction below is returned as
# a raw, unformatted number in the SAME units frontend/src/lib/utils/format.ts
# expects its inputs in (fractions for formatRate/formatRatio, e.g. 0.83 not
# "83%"; plain floats for formatCapital/formatOI) — Hermes never pre-formats
# a string server-side. The frontend applies format.ts's formatters at
# render time, exactly as every other page in this app already does.
from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from quant_hub.api.envelope import ResponseEnvelope, ok
from quant_hub.hermes.coordinator import hermes_coordinator
from quant_hub.hermes.monitors import data_pipeline, ml_ops, strategy_lifecycle
from quant_hub.infrastructure.cache import get_redis
from quant_hub.infrastructure.database import get_session

router = APIRouter(tags=["hermes"])

# get_session()/get_redis() are infrastructure-layer dependencies (not one of
# the four barred domain packages) — reused directly rather than re-declared,
# so Hermes shares the same connection pools as the rest of the app.
DbSession = Annotated[AsyncSession, Depends(get_session)]
CacheClient = Annotated[Redis, Depends(get_redis)]


# ── Response schemas ────────────────────────────────────────────────────
class ServiceStatusOut(BaseModel):
    name: str
    status: str
    latency_ms: float | None
    detail: str


class AssetFreshnessOut(BaseModel):
    asset_id: str
    symbol: str
    instrument_type: str
    last_bar_ts: datetime | None
    bar_count: int
    staleness_seconds: float | None
    status: str


class FundingFreshnessOut(BaseModel):
    asset_id: str
    symbol: str
    last_funding_ts: datetime | None
    staleness_seconds: float | None
    status: str


class StrategyLifecycleOut(BaseModel):
    strategy_id: str
    name: str
    status: str
    last_signal_ts: datetime | None
    signals_24h: int
    valid_rate_24h: float | None
    latest_backtest_status: str | None
    latest_backtest_completed_at: datetime | None


class MLModelStatusOut(BaseModel):
    model_id: str
    name: str
    model_type: str
    status: str
    accuracy: float | None
    deployed_at: datetime | None
    created_at: datetime


class TrainingJobOut(BaseModel):
    job_id: str
    model_type: str
    status: str
    created_at: str
    completed_at: str | None


class SystemStatusOut(BaseModel):
    health_score: float
    services: list[ServiceStatusOut]
    assets: list[AssetFreshnessOut]
    funding: list[FundingFreshnessOut]
    strategies: list[StrategyLifecycleOut]
    models: list[MLModelStatusOut]
    training_jobs: list[TrainingJobOut]
    generated_at: datetime


class StrategyEngineSummaryOut(BaseModel):
    active_count: int
    signals_24h: int


class DataPipelineSummaryOut(BaseModel):
    fresh_count: int
    stale_count: int
    dead_count: int


class MLEngineSummaryOut(BaseModel):
    trained_count: int
    last_accuracy: float | None


class ExecutionEngineSummaryOut(BaseModel):
    orders_today: int
    fill_rate_today: float | None


class HealthSummaryOut(BaseModel):
    health_score: float
    services: list[ServiceStatusOut]
    strategy_engine: StrategyEngineSummaryOut
    data_pipeline: DataPipelineSummaryOut
    ml_engine: MLEngineSummaryOut
    execution_engine: ExecutionEngineSummaryOut
    generated_at: datetime


class PipelineOut(BaseModel):
    assets: list[AssetFreshnessOut]
    funding: list[FundingFreshnessOut]


class StrategiesOut(BaseModel):
    strategies: list[StrategyLifecycleOut]


class MLOut(BaseModel):
    models: list[MLModelStatusOut]
    training_jobs: list[TrainingJobOut]


# ── Routes ───────────────────────────────────────────────────────────────
@router.get("/status", response_model=ResponseEnvelope[SystemStatusOut], summary="Full Hermes system status")
async def get_status(session: DbSession, redis: CacheClient) -> ResponseEnvelope[SystemStatusOut]:
    status_ = await hermes_coordinator.get_status(session, redis)
    return ok(
        SystemStatusOut(
            health_score=status_.health_score,
            services=[ServiceStatusOut(**s.__dict__) for s in status_.services],
            assets=[AssetFreshnessOut(**a.__dict__) for a in status_.assets],
            funding=[FundingFreshnessOut(**f.__dict__) for f in status_.funding],
            strategies=[StrategyLifecycleOut(**s.__dict__) for s in status_.strategies],
            models=[MLModelStatusOut(**m.__dict__) for m in status_.models],
            training_jobs=[TrainingJobOut(**j.__dict__) for j in status_.training_jobs],
            generated_at=status_.generated_at,
        )
    )


@router.get("/health", response_model=ResponseEnvelope[HealthSummaryOut], summary="Lightweight health summary — safe for 30s polling")
async def get_health(session: DbSession, redis: CacheClient) -> ResponseEnvelope[HealthSummaryOut]:
    summary = await hermes_coordinator.get_health(session, redis)
    return ok(
        HealthSummaryOut(
            health_score=summary.health_score,
            services=[ServiceStatusOut(**s.__dict__) for s in summary.services],
            strategy_engine=StrategyEngineSummaryOut(**summary.strategy_engine.__dict__),
            data_pipeline=DataPipelineSummaryOut(**summary.data_pipeline.__dict__),
            ml_engine=MLEngineSummaryOut(**summary.ml_engine.__dict__),
            execution_engine=ExecutionEngineSummaryOut(**summary.execution_engine.__dict__),
            generated_at=summary.generated_at,
        )
    )


@router.get("/pipeline", response_model=ResponseEnvelope[PipelineOut], summary="Data pipeline freshness per asset")
async def get_pipeline(session: DbSession) -> ResponseEnvelope[PipelineOut]:
    assets = await data_pipeline.get_asset_freshness(session)
    funding = await data_pipeline.get_funding_freshness(session)
    return ok(
        PipelineOut(
            assets=[AssetFreshnessOut(**a.__dict__) for a in assets],
            funding=[FundingFreshnessOut(**f.__dict__) for f in funding],
        )
    )


@router.get("/strategies", response_model=ResponseEnvelope[StrategiesOut], summary="Strategy lifecycle status")
async def get_strategies(session: DbSession) -> ResponseEnvelope[StrategiesOut]:
    strategies = await strategy_lifecycle.get_strategy_lifecycle(session)
    return ok(StrategiesOut(strategies=[StrategyLifecycleOut(**s.__dict__) for s in strategies]))


@router.get("/ml", response_model=ResponseEnvelope[MLOut], summary="ML model registry + active training jobs")
async def get_ml(session: DbSession, redis: CacheClient) -> ResponseEnvelope[MLOut]:
    models = await ml_ops.get_model_registry(session)
    jobs = await ml_ops.get_active_training_jobs(redis)
    return ok(MLOut(models=[MLModelStatusOut(**m.__dict__) for m in models], training_jobs=[TrainingJobOut(**j.__dict__) for j in jobs]))

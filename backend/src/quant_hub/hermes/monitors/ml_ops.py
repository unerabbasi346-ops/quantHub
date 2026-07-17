# Hermes monitor: ML model registry + in-flight training jobs. Reads
# analytics.ml_models directly via raw SQL (not the ml_models repository —
# kept consistent with every other Hermes monitor's read-only-SQL pattern,
# even though quant_hub.domain.ml isn't one of the four barred domains) and
# Redis for job status, using the SAME `ml:train:{job_id}` key convention
# api/ml.py's training endpoint writes (see that module's _run_training/
# train_model) — duplicated here as a read-only key format, not a shared
# import, so this monitor never depends on the training endpoint's code.
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_ACTIVE_JOB_STATUSES = {"PENDING", "RUNNING"}
_TRAIN_JOB_KEY_PREFIX = "ml:train:"


@dataclass(frozen=True)
class MLModelStatus:
    model_id: str
    name: str
    model_type: str
    status: str
    accuracy: float | None
    # Majority-class baseline from metrics JSONB (api/ml.py's _run_training) —
    # null for models trained before baseline gating existed.
    baseline: float | None
    # Training-data date span from metrics JSONB — null for legacy rows.
    period_start: str | None
    period_end: str | None
    deployed_at: datetime | None
    created_at: datetime


@dataclass(frozen=True)
class TrainingJob:
    job_id: str
    model_type: str
    status: str
    created_at: str
    completed_at: str | None


async def get_model_registry(session: AsyncSession, limit: int = 20) -> list[MLModelStatus]:
    rows = (
        await session.execute(
            text(
                """
                SELECT id, name, model_type, status, metrics, deployed_at, created_at
                FROM analytics.ml_models
                ORDER BY created_at DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        )
    ).all()

    out: list[MLModelStatus] = []
    for row in rows:
        accuracy = None
        baseline = None
        period_start = None
        period_end = None
        if row.metrics and isinstance(row.metrics, dict):
            raw = row.metrics.get("accuracy")
            if isinstance(raw, (int, float)):
                accuracy = float(raw)
            raw_baseline = row.metrics.get("baseline")
            if isinstance(raw_baseline, (int, float)):
                baseline = float(raw_baseline)
            ps, pe = row.metrics.get("period_start"), row.metrics.get("period_end")
            period_start = ps if isinstance(ps, str) else None
            period_end = pe if isinstance(pe, str) else None
        out.append(
            MLModelStatus(
                model_id=str(row.id),
                name=row.name,
                model_type=row.model_type,
                status=row.status,
                accuracy=accuracy,
                baseline=baseline,
                period_start=period_start,
                period_end=period_end,
                deployed_at=row.deployed_at,
                created_at=row.created_at,
            )
        )
    return out


async def get_active_training_jobs(redis: Redis) -> list[TrainingJob]:
    jobs: list[TrainingJob] = []
    async for key in redis.scan_iter(match=f"{_TRAIN_JOB_KEY_PREFIX}*"):
        raw = await redis.get(key)
        if not raw:
            continue
        payload = json.loads(raw)
        if payload.get("status") not in _ACTIVE_JOB_STATUSES:
            continue
        job_id = key[len(_TRAIN_JOB_KEY_PREFIX):] if isinstance(key, str) else key.decode()[len(_TRAIN_JOB_KEY_PREFIX):]
        jobs.append(
            TrainingJob(
                job_id=job_id,
                model_type=payload.get("model_type", "unknown"),
                status=payload["status"],
                created_at=payload.get("created_at", ""),
                completed_at=payload.get("completed_at"),
            )
        )
    return jobs

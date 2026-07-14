# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
#   §Background Processing: long-running tasks execute asynchronously.
# Doc 03 — Technology Stack §Quantitative Libraries.
# Doc 09 — Database Architecture (analytics.ml_models).
# Per Doc 00 §14.11
#
# NOT versioned under /v1 (mounted at /api/ml directly in main.py, per the
# task's explicit path) — a deliberately separate surface from the governed
# REST API every other feature slice registers under api/v1/router.py.
#
# BACKGROUND PROCESSING (JUDGMENT CALL, §14.5/§14.7 flagged): training runs
# via FastAPI's BackgroundTasks, per explicit instruction ("no new
# queue/worker"). This still executes ON the request-handling event loop
# after the response is sent — CPU-bound model.fit() calls (XGBoost/PyTorch)
# block that loop for their duration, unlike a real task queue (Celery/RQ)
# that would run in a separate worker process. Acceptable for this scoped
# feature; flagged so a future high-throughput training load doesn't
# silently inherit this limitation unnoticed.
#
# JOB STATUS STORAGE: Redis (infrastructure/cache.py), already wired and
# live in this environment — no new dependency introduced. A 24h TTL keeps
# job records from growing unbounded; there is no requirement to retain them
# longer, and this is not a governed audit record (unlike core.orders/
# core.executions, which ARE permanent per P-5).
#
# MODEL ARTIFACT STORAGE: backend/artifacts/ml/{model_type}/{job_id}.joblib —
# reuses the existing `artifacts/` gitignore convention (see .gitignore's
# "Trained model artifacts... regenerable" note) rather than inventing a new
# ignored-directory pattern.
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid7

import numpy as np
import pandas as pd
from fastapi import APIRouter, BackgroundTasks, status
from pydantic import BaseModel, Field

from quant_hub.api.dependencies import CacheClient, MLModelRepo
from quant_hub.api.envelope import ApiError, ErrorCode, ResponseEnvelope, ok
from quant_hub.infrastructure.database import AsyncSessionLocal
from quant_hub.ml.ml_engine import HMMRegimeDetector, XGBoostMetaLabeler
from quant_hub.ml.model_factory import create_model, registered_model_types
from quant_hub.persistence.repositories.ml_models import SQLAlchemyMLModelRepository

router = APIRouter(tags=["ml"])

_ARTIFACT_ROOT = Path(__file__).resolve().parents[3] / "artifacts" / "ml"
_JOB_TTL_SECONDS = 24 * 60 * 60

_FRAMEWORK_BY_TYPE = {
    "XGBoost_MetaLabeler": "xgboost",
    "LSTM_Predictor": "pytorch",
    "HMM_RegimeDetector": "hmmlearn",
}


def _jsonable(value: Any) -> Any:
    """Recursively convert numpy scalars/arrays (model.evaluate()'s native
    output type) into plain Python types JSON/Redis can serialize. Never
    fabricates a value — a straight type coercion of the model's own real
    output.
    """
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, np.ndarray):
        return [_jsonable(v) for v in value.tolist()]
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None  # NaN/Infinity has no JSON literal — honest null
    return value


def _to_feature_frame(feature_data: list[list[float]]) -> pd.DataFrame:
    if not feature_data:
        raise ValueError("feature_data must be non-empty")
    width = len(feature_data[0])
    return pd.DataFrame(feature_data, columns=[f"f{i}" for i in range(width)])


class TrainRequest(BaseModel):
    model_type: str
    hyperparams: dict[str, Any] = Field(default_factory=dict)
    feature_data: list[list[float]]
    target_data: list[float]


class TrainJobOut(BaseModel):
    job_id: str


class TrainStatusOut(BaseModel):
    job_id: str
    status: str  # PENDING | RUNNING | COMPLETED | FAILED
    model_type: str
    created_at: str
    completed_at: str | None = None
    metrics: dict[str, Any] | None = None
    error: str | None = None


async def _run_training(
    job_id: str,
    model_type: str,
    hyperparams: dict[str, Any],
    feature_data: list[list[float]],
    target_data: list[float],
    redis: Any,
) -> None:
    """The actual training work, run via BackgroundTasks after the response
    is sent. Opens its OWN database session (the request's session is
    already closed by the time this runs) — same convention as every
    one-off script in scripts/ that runs outside a request lifecycle.
    """
    key = f"ml:train:{job_id}"

    async def _set_status(payload: dict[str, Any]) -> None:
        await redis.set(key, json.dumps(payload), ex=_JOB_TTL_SECONDS)

    base = json.loads(await redis.get(key))
    base["status"] = "RUNNING"
    await _set_status(base)

    try:
        X = _to_feature_frame(feature_data)
        y = pd.Series(target_data)
        model = create_model(model_type, hyperparams)
        model.train(X, y)
        metrics = _jsonable(model.evaluate(X, y))

        artifact_dir = _ARTIFACT_ROOT / model_type
        artifact_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = str(artifact_dir / f"{job_id}.joblib")
        model.save_model(artifact_path)

        async with AsyncSessionLocal() as session:
            repo = SQLAlchemyMLModelRepository(session)
            await repo.register_trained(
                model_type=model_type,
                version=job_id,
                framework=_FRAMEWORK_BY_TYPE.get(model_type, "unknown"),
                artifact_path=artifact_path,
                config=hyperparams,
                metrics=metrics,
            )
            await session.commit()

        base["status"] = "COMPLETED"
        base["completed_at"] = datetime.now(timezone.utc).isoformat()
        base["metrics"] = metrics
        await _set_status(base)
    except Exception as exc:  # noqa: BLE001 — surfaced via job status, never swallowed
        base["status"] = "FAILED"
        base["completed_at"] = datetime.now(timezone.utc).isoformat()
        base["error"] = str(exc)
        await _set_status(base)


@router.post(
    "/train",
    response_model=ResponseEnvelope[TrainJobOut],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start training a registered model type in the background",
)
async def train_model(
    body: TrainRequest,
    background_tasks: BackgroundTasks,
    redis: CacheClient,
) -> ResponseEnvelope[TrainJobOut]:
    if body.model_type not in registered_model_types():
        raise ApiError(
            status.HTTP_400_BAD_REQUEST,
            ErrorCode.VALIDATION_ERROR,
            f"Unknown model_type {body.model_type!r}. Registered types: {registered_model_types()}",
        )
    if not body.feature_data or not body.target_data:
        raise ApiError(
            status.HTTP_400_BAD_REQUEST,
            ErrorCode.VALIDATION_ERROR,
            "feature_data and target_data must both be non-empty",
        )

    job_id = str(uuid7())
    created_at = datetime.now(timezone.utc).isoformat()
    await redis.set(
        f"ml:train:{job_id}",
        json.dumps({"status": "PENDING", "model_type": body.model_type, "created_at": created_at}),
        ex=_JOB_TTL_SECONDS,
    )
    background_tasks.add_task(
        _run_training, job_id, body.model_type, body.hyperparams, body.feature_data, body.target_data, redis
    )
    return ok(TrainJobOut(job_id=job_id))


@router.get(
    "/train/{job_id}/status",
    response_model=ResponseEnvelope[TrainStatusOut],
    summary="Get a training job's status/result",
)
async def get_train_status(job_id: str, redis: CacheClient) -> ResponseEnvelope[TrainStatusOut]:
    raw = await redis.get(f"ml:train:{job_id}")
    if raw is None:
        raise ApiError(
            status.HTTP_404_NOT_FOUND,
            ErrorCode.RESOURCE_NOT_FOUND,
            f"No training job {job_id} found (expired after {_JOB_TTL_SECONDS // 3600}h or never existed)",
        )
    data = json.loads(raw)
    return ok(TrainStatusOut(job_id=job_id, **data))


class PredictRequest(BaseModel):
    model_type: str
    feature_data: list[list[float]]


class PredictOut(BaseModel):
    predictions: list[float]
    probabilities: list[float] | None = None
    confidence: list[float] | None = None
    note: str | None = None


@router.post(
    "/predict",
    response_model=ResponseEnvelope[PredictOut],
    summary="Run inference against the latest deployed model of a given type",
)
async def predict(body: PredictRequest, ml_repo: MLModelRepo) -> ResponseEnvelope[PredictOut]:
    if body.model_type not in registered_model_types():
        raise ApiError(
            status.HTTP_400_BAD_REQUEST,
            ErrorCode.VALIDATION_ERROR,
            f"Unknown model_type {body.model_type!r}. Registered types: {registered_model_types()}",
        )
    record = await ml_repo.get_latest_deployed(body.model_type)
    if record is None:
        raise ApiError(
            status.HTTP_404_NOT_FOUND,
            ErrorCode.RESOURCE_NOT_FOUND,
            f"No deployed model for model_type {body.model_type!r} — train one first via POST /api/ml/train",
        )

    model = create_model(body.model_type, dict(record.config))
    model.load_model(record.artifact_path)
    X = _to_feature_frame(body.feature_data)
    raw_preds = model.predict(X)
    predictions = [float(v) for v in np.asarray(raw_preds).flatten()]

    # Response shape differs genuinely by model semantics — never a
    # uniform fabricated "confidence" the model type doesn't actually produce.
    if isinstance(model, XGBoostMetaLabeler):
        # predict() already IS P(profitable); confidence = P(predicted class).
        probabilities = predictions
        confidence = [max(p, 1 - p) for p in predictions]
        return ok(PredictOut(predictions=predictions, probabilities=probabilities, confidence=confidence))

    if isinstance(model, HMMRegimeDetector):
        # hmmlearn's GaussianHMM exposes real posterior state probabilities —
        # confidence = the predicted regime's own posterior probability.
        X_scaled = model.scaler.transform(X)
        state_probs = model.model.predict_proba(X_scaled)
        confidence = [float(row.max()) for row in state_probs]
        return ok(
            PredictOut(
                predictions=predictions,
                probabilities=None,
                confidence=confidence,
                note="confidence = max posterior state probability (hmmlearn predict_proba); "
                     "HMM regimes have no single 'probability of being correct' figure",
            )
        )

    # LSTMPredictor: a raw regression output — probability/confidence has no
    # meaning for a point forecast; never fabricated.
    return ok(
        PredictOut(
            predictions=predictions,
            probabilities=None,
            confidence=None,
            note="regression model — no probability/confidence concept applies to a point forecast",
        )
    )

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


class TrainMetalabelerRequest(BaseModel):
    """Research-page training: the server builds the REAL labeled dataset
    (quant_hub.ml.training_data — every recorded signal, point-in-time
    features, realized forward-return labels) for one instrument type, so no
    caller ever has to fabricate feature/target arrays."""

    instrument_type: str = "SPOT"  # SPOT | PERPETUAL — selects the feature set
    horizon_bars: int = Field(24, ge=1, le=720)
    hyperparams: dict[str, Any] = Field(default_factory=dict)


async def _run_metalabeler_training(
    job_id: str, instrument_type: str, horizon_bars: int, hyperparams: dict[str, Any], redis: Any
) -> None:
    """Background job mirroring scripts/retrain_metalabeler.py exactly:
    chronological 80/20 split, held-out metrics vs the majority-class
    baseline, and deployment ONLY when the model beats that baseline."""
    from quant_hub.ml.feature_engineering import feature_mask, feature_names_for
    from quant_hub.ml.training_data import build_metalabeler_datasets

    key = f"ml:train:{job_id}"

    async def _set_status(payload: dict[str, Any]) -> None:
        await redis.set(key, json.dumps(payload), ex=_JOB_TTL_SECONDS)

    base = json.loads(await redis.get(key))
    base["status"] = "RUNNING"
    await _set_status(base)

    try:
        datasets = await build_metalabeler_datasets(horizon_bars)
        if instrument_type not in datasets:
            raise ValueError(
                f"No labelable {instrument_type} signals exist (missing bar history "
                f"or no recorded signals for that instrument type)"
            )
        X, y = datasets[instrument_type]
        if len(X) < 50:
            raise ValueError(f"Only {len(X)} labeled {instrument_type} signals — need >= 50 to train")

        split = int(len(X) * 0.8)
        X_train, X_test = X.iloc[:split], X.iloc[split:]
        y_train, y_test = y.iloc[:split], y.iloc[split:]

        model = create_model("XGBoost_MetaLabeler", hyperparams)
        model.train(X_train, y_train)
        eval_metrics = _jsonable(model.evaluate(X_test, y_test))

        baseline = max(float(y_test.mean()), 1.0 - float(y_test.mean()))
        accuracy = float(eval_metrics["accuracy"])
        beats_baseline = accuracy > baseline

        period_start, period_end = await _signal_period(instrument_type)
        metrics: dict[str, Any] = {
            **eval_metrics,
            "baseline": baseline,
            "beats_baseline": beats_baseline,
            "deployed": beats_baseline,
            "train_rows": len(X_train),
            "test_rows": len(X_test),
            "horizon_bars": horizon_bars,
            "instrument_type": instrument_type,
            "features": list(feature_names_for(instrument_type)),
            "feature_mask": feature_mask(instrument_type),
            "period_start": period_start,
            "period_end": period_end,
        }

        if beats_baseline:
            model_type = f"XGBoost_MetaLabeler_{instrument_type}"
            artifact_dir = _ARTIFACT_ROOT / model_type
            artifact_dir.mkdir(parents=True, exist_ok=True)
            artifact_path = str(artifact_dir / f"{job_id}.joblib")
            model.save_model(artifact_path)
            async with AsyncSessionLocal() as session:
                repo = SQLAlchemyMLModelRepository(session)
                await repo.register_trained(
                    model_type=model_type, version=job_id, framework="xgboost",
                    artifact_path=artifact_path, config=hyperparams, metrics=metrics,
                )
                await session.commit()
        else:
            metrics["not_deployed_reason"] = (
                f"held-out accuracy {accuracy:.4f} <= majority-class baseline {baseline:.4f} — "
                "model adds nothing over always predicting the majority class"
            )

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
    "/train/metalabeler",
    response_model=ResponseEnvelope[TrainJobOut],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Train the metalabeler on the real signal dataset (server-built), baseline-gated deploy",
)
async def train_metalabeler(
    body: TrainMetalabelerRequest,
    background_tasks: BackgroundTasks,
    redis: CacheClient,
) -> ResponseEnvelope[TrainJobOut]:
    if body.instrument_type not in ("SPOT", "PERPETUAL"):
        raise ApiError(
            status.HTTP_400_BAD_REQUEST,
            ErrorCode.VALIDATION_ERROR,
            "instrument_type must be SPOT or PERPETUAL",
        )
    job_id = str(uuid7())
    created_at = datetime.now(timezone.utc).isoformat()
    await redis.set(
        f"ml:train:{job_id}",
        json.dumps({
            "status": "PENDING",
            "model_type": f"XGBoost_MetaLabeler_{body.instrument_type}",
            "created_at": created_at,
        }),
        ex=_JOB_TTL_SECONDS,
    )
    background_tasks.add_task(
        _run_metalabeler_training, job_id, body.instrument_type, body.horizon_bars, body.hyperparams, redis
    )
    return ok(TrainJobOut(job_id=job_id))


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


# ══════════════════════════════════════════════════════════════════════════
# LSTM + HMM server-built training (Research page) — same job/status plumbing
# as the metalabeler above; each gates or evaluates per its own semantics.
# ══════════════════════════════════════════════════════════════════════════


async def _signal_period(instrument_type: str) -> tuple[str | None, str | None]:
    """Min/max signal timestamp for an instrument type — the real date span
    the metalabeler/LSTM training dataset was drawn from (for the UI's
    'training period' card). Honest nulls if no signals exist."""
    from sqlalchemy import text as _sa_text

    async with AsyncSessionLocal() as session:
        row = (
            await session.execute(
                _sa_text(
                    """
                    SELECT MIN(s.ts) lo, MAX(s.ts) hi
                    FROM core.signals s
                    JOIN market_data.assets a ON a.id = s.asset_id
                    WHERE a.instrument_type = :it
                    """
                ),
                {"it": instrument_type},
            )
        ).first()
    if row is None or row.lo is None:
        return None, None
    return row.lo.isoformat(), row.hi.isoformat()

class TrainLstmRequest(BaseModel):
    """Server builds the same real labeled signal dataset as the metalabeler;
    the LSTM consumes it as feature sequences (seq_length lookback)."""

    instrument_type: str = "SPOT"
    horizon_bars: int = Field(24, ge=1, le=720)
    seq_length: int = Field(20, ge=2, le=100)
    hyperparams: dict[str, Any] = Field(default_factory=dict)


_LSTM_MIN_SIGNALS = 500


async def _run_lstm_training(
    job_id: str, instrument_type: str, horizon_bars: int, seq_length: int,
    hyperparams: dict[str, Any], redis: Any,
) -> None:
    """LSTM on the real signal dataset: chronological 80/20 split, per-row
    sliding-window predictions on the held-out tail, accuracy vs the
    majority-class baseline, deploy only if it beats the baseline."""
    import torch as _torch
    import torch.nn as _nn

    from quant_hub.ml.feature_engineering import feature_names_for
    from quant_hub.ml.training_data import build_metalabeler_datasets

    key = f"ml:train:{job_id}"

    async def _set_status(payload: dict[str, Any]) -> None:
        await redis.set(key, json.dumps(payload), ex=_JOB_TTL_SECONDS)

    base = json.loads(await redis.get(key))
    base["status"] = "RUNNING"
    await _set_status(base)

    try:
        datasets = await build_metalabeler_datasets(horizon_bars)
        if instrument_type not in datasets:
            raise ValueError(f"No labelable {instrument_type} signals exist")
        X, y = datasets[instrument_type]
        if len(X) < _LSTM_MIN_SIGNALS:
            raise ValueError(
                f"Only {len(X)} labeled {instrument_type} signals — LSTM needs >= {_LSTM_MIN_SIGNALS} "
                f"({_LSTM_MIN_SIGNALS - len(X)} more required)"
            )

        n_features = X.shape[1]
        params = {"input_dim": n_features, "seq_length": seq_length, **hyperparams}
        split = int(len(X) * 0.8)
        X_train, X_test = X.iloc[:split], X.iloc[split:]
        y_train, y_test = y.iloc[:split], y.iloc[split:]

        model = create_model("LSTM_Predictor", params)
        model.train(X_train, y_train)

        # Held-out per-row predictions: each test row scored from its own
        # trailing seq_length feature window (train tail + test prefix), the
        # same information a live inference call would have.
        X_all_scaled = model.scaler.transform(X)
        preds: list[float] = []
        _nn.Module.train(model, False)
        with _torch.no_grad():
            for i in range(split, len(X)):
                lo = max(0, i - seq_length)
                window = _torch.tensor(X_all_scaled[lo:i + 1], dtype=_torch.float32).unsqueeze(0)
                out, _ = model.lstm(window)
                preds.append(float(model.linear(out[:, -1, :]).item()))

        pred_labels = [1 if p > 0.5 else 0 for p in preds]
        y_true = y_test.tolist()
        accuracy = float(np.mean([pl == yt for pl, yt in zip(pred_labels, y_true)]))
        baseline = max(float(y_test.mean()), 1.0 - float(y_test.mean()))
        beats_baseline = accuracy > baseline

        from sklearn.metrics import precision_score, recall_score

        period_start, period_end = await _signal_period(instrument_type)
        metrics: dict[str, Any] = {
            "accuracy": accuracy,
            "precision": float(precision_score(y_true, pred_labels, zero_division=0)),
            "recall": float(recall_score(y_true, pred_labels, zero_division=0)),
            "baseline": baseline,
            "beats_baseline": beats_baseline,
            "deployed": beats_baseline,
            "train_rows": len(X_train),
            "test_rows": len(X_test),
            "horizon_bars": horizon_bars,
            "seq_length": seq_length,
            "instrument_type": instrument_type,
            "features": list(feature_names_for(instrument_type)),
            "period_start": period_start,
            "period_end": period_end,
        }
        if beats_baseline:
            model_type = f"LSTM_Predictor_{instrument_type}"
            artifact_dir = _ARTIFACT_ROOT / model_type
            artifact_dir.mkdir(parents=True, exist_ok=True)
            artifact_path = str(artifact_dir / f"{job_id}.joblib")
            model.save_model(artifact_path)
            async with AsyncSessionLocal() as session:
                repo = SQLAlchemyMLModelRepository(session)
                await repo.register_trained(
                    model_type=model_type, version=job_id, framework="pytorch",
                    artifact_path=artifact_path, config=params, metrics=metrics,
                )
                await session.commit()
        else:
            metrics["not_deployed_reason"] = (
                f"held-out accuracy {accuracy:.4f} <= majority-class baseline {baseline:.4f}"
            )

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
    "/train/lstm",
    response_model=ResponseEnvelope[TrainJobOut],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Train the LSTM predictor on the real signal dataset (server-built), baseline-gated deploy",
)
async def train_lstm(
    body: TrainLstmRequest,
    background_tasks: BackgroundTasks,
    redis: CacheClient,
) -> ResponseEnvelope[TrainJobOut]:
    if body.instrument_type not in ("SPOT", "PERPETUAL"):
        raise ApiError(
            status.HTTP_400_BAD_REQUEST, ErrorCode.VALIDATION_ERROR,
            "instrument_type must be SPOT or PERPETUAL",
        )
    job_id = str(uuid7())
    await redis.set(
        f"ml:train:{job_id}",
        json.dumps({
            "status": "PENDING",
            "model_type": f"LSTM_Predictor_{body.instrument_type}",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }),
        ex=_JOB_TTL_SECONDS,
    )
    background_tasks.add_task(
        _run_lstm_training, job_id, body.instrument_type, body.horizon_bars, body.seq_length,
        body.hyperparams, redis,
    )
    return ok(TrainJobOut(job_id=job_id))


class TrainHmmRequest(BaseModel):
    """HMM regime detection trains on real bar data directly (returns +
    rolling volatility) — no signals involved."""

    symbol: str = "BTC/USDT"
    exchange: str = "binance"
    interval: str = "1h"
    hyperparams: dict[str, Any] = Field(default_factory=dict)


_HMM_MIN_BARS = 500
_HMM_VOL_WINDOW = 24
_REGIME_LABELS = {0: "bear", 1: "neutral", 2: "bull"}


async def _run_hmm_training(
    job_id: str, symbol: str, exchange: str, interval: str,
    hyperparams: dict[str, Any], redis: Any,
) -> None:
    """HMM on [return, rolling vol] of real bars. Unsupervised — no accuracy
    gate; metrics carry regime distribution, average durations, a downsampled
    regime history, and the current regime with posterior confidence."""
    from quant_hub.persistence.repositories.market_data import (
        SQLAlchemyAssetRepository,
        SQLAlchemyOHLCVRepository,
    )

    key = f"ml:train:{job_id}"

    async def _set_status(payload: dict[str, Any]) -> None:
        await redis.set(key, json.dumps(payload), ex=_JOB_TTL_SECONDS)

    base = json.loads(await redis.get(key))
    base["status"] = "RUNNING"
    await _set_status(base)

    try:
        async with AsyncSessionLocal() as session:
            assets = SQLAlchemyAssetRepository(session)
            asset_id = await assets.get_by_symbol_exchange(symbol, exchange)
            if asset_id is None:
                raise ValueError(f"No ingested asset {symbol}@{exchange}")
            bars = await SQLAlchemyOHLCVRepository(session).get_bars(asset_id, interval, limit=200_000)
        if len(bars) < _HMM_MIN_BARS:
            raise ValueError(
                f"Only {len(bars)} {interval} bars for {symbol} — HMM needs >= {_HMM_MIN_BARS}"
            )

        closes = pd.Series([float(b.close) for b in bars])
        volumes = pd.Series([float(b.volume) for b in bars])
        ts = [b.ts for b in bars]
        returns = closes.pct_change()
        vol = returns.rolling(_HMM_VOL_WINDOW).std()
        # Observation matrix — the prompt's four conceptual dimensions. funding
        # / open-interest are 0 for a SPOT asset; a zero-variance column would
        # make GaussianHMM's "full" covariance singular, so constant columns
        # are dropped before fitting (data_features records the full intended
        # set; feature_columns records what actually fed the model).
        volume_ratio = volumes / volumes.rolling(_HMM_VOL_WINDOW).mean()
        candidates = pd.DataFrame({
            "returns": returns,
            "volume_ratio": volume_ratio,
            "funding_rate": 0.0,           # SPOT — no funding stream
            "open_interest": 0.0,          # SPOT — no OI stream
            "volatility": vol,
        }).dropna()
        offset = len(closes) - len(candidates)  # first usable bar index
        used_cols = [c for c in candidates.columns if candidates[c].nunique() > 1]
        frame = candidates[used_cols]

        model = create_model("HMM_RegimeDetector", hyperparams)
        model.train(frame)
        regimes = model.predict(frame)  # already mapped 0=bear/1=neutral/2=bull

        # Per-timestep posteriors, mapped raw-state -> regime label.
        X_scaled = model.scaler.transform(frame)
        raw_post = model.model.predict_proba(X_scaled)
        n_comp = model.params["n_components"]
        # regime_mapping: raw_state -> regime index (bijection). Invert it.
        raw_for_regime = {v: k for k, v in model.regime_mapping.items()}
        regime_post = np.column_stack([
            raw_post[:, raw_for_regime[r]] if r in raw_for_regime else np.zeros(len(raw_post))
            for r in range(n_comp)
        ])
        current_regime = int(regimes[-1])
        current_confidence = float(regime_post[-1][current_regime])

        counts = {int(r): int((regimes == r).sum()) for r in range(n_comp)}

        # Average regime duration (consecutive same-regime runs), in bars/hours.
        durations_by_regime: dict[int, list[int]] = {r: [] for r in range(n_comp)}
        run_r, run_len = int(regimes[0]), 1
        for r in regimes[1:]:
            if int(r) == run_r:
                run_len += 1
            else:
                durations_by_regime[run_r].append(run_len)
                run_r, run_len = int(r), 1
        durations_by_regime[run_r].append(run_len)
        hours_per_bar = 24 if interval == "1d" else 1
        avg_duration_hours = {
            _REGIME_LABELS[r]: (float(np.mean(v)) * hours_per_bar if v else 0.0)
            for r, v in durations_by_regime.items()
        }
        avg_duration_bars = float(np.mean([len(regimes)] + [d for v in durations_by_regime.values() for d in v]))

        # Transition matrix in regime order (rows/cols = bear/neutral/bull).
        raw_trans = model.model.transmat_
        transition_matrix = [
            [float(raw_trans[raw_for_regime[i]][raw_for_regime[j]]) for j in range(n_comp)]
            for i in range(n_comp)
        ]
        # P(regime changes within 24 bars) = 1 - P(stay)^24 for current regime.
        p_stay = transition_matrix[current_regime][current_regime]
        regime_change_prob_24h = float(1.0 - p_stay ** (24 // hours_per_bar))
        # Transition entropy (stability): avg row entropy, lower = more stable.
        import math as _math
        transition_entropy = float(np.mean([
            -sum(p * _math.log(p) for p in row if p > 0) for row in transition_matrix
        ]))

        # Daily posterior bands for a smooth timeline — average the 3-regime
        # posterior within each calendar day (kills the hourly flicker).
        post_df = pd.DataFrame(regime_post, columns=["bear", "neutral", "bull"][:n_comp])
        post_df["day"] = [ts[offset + i].date().isoformat() for i in range(len(post_df))]
        daily = post_df.groupby("day", sort=True).mean()
        regime_posteriors = [
            {"ts": day, **{k: float(daily.loc[day, k]) for k in daily.columns}}
            for day in daily.index
        ]
        # Backwards-compatible discrete history (still consumed by the old chart).
        stride = max(1, len(regimes) // 500)
        history = [
            {"ts": ts[offset + i].isoformat(), "regime": int(regimes[i])}
            for i in range(0, len(regimes), stride)
        ]

        metrics: dict[str, Any] = {
            "symbol": symbol,
            "interval": interval,
            "bars_used": len(frame),
            "regime_labels": _REGIME_LABELS,
            "regime_distribution": counts,
            "regime_counts": {_REGIME_LABELS[r]: c for r, c in counts.items()},
            "avg_durations": _jsonable(model.evaluate(frame)),
            "avg_duration_hours": avg_duration_hours,
            "avg_duration_bars": avg_duration_bars,
            "transition_matrix": transition_matrix,
            "transition_entropy": transition_entropy,
            "regime_change_prob_24h": regime_change_prob_24h,
            "current_regime": current_regime,
            "current_regime_label": _REGIME_LABELS.get(current_regime, str(current_regime)),
            "current_regime_posterior": current_confidence,
            "current_confidence": current_confidence,
            "regime_history": history,
            "regime_posteriors": regime_posteriors,
            "data_features": ["returns", "volume_ratio", "funding_rate", "open_interest"],
            "feature_columns": used_cols,
            "period_start": ts[offset].isoformat(),
            "period_end": ts[-1].isoformat(),
        }

        model_type = "HMM_RegimeDetector"
        artifact_dir = _ARTIFACT_ROOT / model_type
        artifact_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = str(artifact_dir / f"{job_id}.joblib")
        model.save_model(artifact_path)
        async with AsyncSessionLocal() as session:
            repo = SQLAlchemyMLModelRepository(session)
            await repo.register_trained(
                model_type=model_type, version=job_id, framework="hmmlearn",
                artifact_path=artifact_path,
                config={"symbol": symbol, "interval": interval, **hyperparams},
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
    "/train/hmm",
    response_model=ResponseEnvelope[TrainJobOut],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Train the HMM regime detector on real bar returns (no accuracy gate)",
)
async def train_hmm(
    body: TrainHmmRequest,
    background_tasks: BackgroundTasks,
    redis: CacheClient,
) -> ResponseEnvelope[TrainJobOut]:
    job_id = str(uuid7())
    await redis.set(
        f"ml:train:{job_id}",
        json.dumps({
            "status": "PENDING",
            "model_type": "HMM_RegimeDetector",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }),
        ex=_JOB_TTL_SECONDS,
    )
    background_tasks.add_task(
        _run_hmm_training, job_id, body.symbol, body.exchange, body.interval, body.hyperparams, redis
    )
    return ok(TrainJobOut(job_id=job_id))


class RegimeOut(BaseModel):
    model_id: str
    trained_at: str
    symbol: str | None
    current_regime: int | None
    current_regime_label: str | None
    current_confidence: float | None
    regime_distribution: dict[str, int] | None
    regime_history: list[dict[str, Any]] | None
    # Extended fields (owner request) — the richer regime intelligence the
    # Strategy-page Market Regime + Research training UI render.
    regime_counts: dict[str, int] | None = None
    avg_duration_hours: dict[str, float] | None = None
    transition_matrix: list[list[float]] | None = None
    transition_entropy: float | None = None
    regime_change_prob_24h: float | None = None
    regime_posteriors: list[dict[str, Any]] | None = None
    bars_used: int | None = None
    period_start: str | None = None
    period_end: str | None = None
    data_features: list[str] | None = None


@router.get(
    "/regime",
    response_model=ResponseEnvelope[RegimeOut | None],
    summary="Latest trained HMM regime state (train-time computed, real bars)",
)
async def get_regime() -> ResponseEnvelope[RegimeOut | None]:
    from sqlalchemy import text as _sa_text

    async with AsyncSessionLocal() as session:
        row = (
            await session.execute(
                _sa_text(
                    """
                    SELECT id, created_at, metrics FROM analytics.ml_models
                    WHERE model_type = 'HMM_RegimeDetector' AND metrics ? 'regime_history'
                    ORDER BY created_at DESC LIMIT 1
                    """
                )
            )
        ).first()
    if row is None:
        return ok(None)
    m = row.metrics or {}
    return ok(RegimeOut(
        model_id=str(row.id),
        trained_at=row.created_at.isoformat(),
        symbol=m.get("symbol"),
        current_regime=m.get("current_regime"),
        current_regime_label=m.get("current_regime_label"),
        current_confidence=m.get("current_confidence"),
        regime_distribution={str(k): v for k, v in (m.get("regime_distribution") or {}).items()} or None,
        regime_history=m.get("regime_history"),
        regime_counts=m.get("regime_counts"),
        avg_duration_hours=m.get("avg_duration_hours"),
        transition_matrix=m.get("transition_matrix"),
        transition_entropy=m.get("transition_entropy"),
        regime_change_prob_24h=m.get("regime_change_prob_24h"),
        regime_posteriors=m.get("regime_posteriors"),
        bars_used=m.get("bars_used"),
        period_start=m.get("period_start"),
        period_end=m.get("period_end"),
        data_features=m.get("data_features"),
    ))

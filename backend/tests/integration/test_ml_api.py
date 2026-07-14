# Governing specification: Doc 03 — Technology Stack §Quantitative Libraries.
# Doc 09 — Database Architecture (analytics.ml_models).
# Per Doc 00 §14.11
#
# End-to-end tests against the REAL app, real Postgres, and real Redis (all
# three already live in this environment) — no dependency overrides. The
# training endpoint's background task opens its own real database session
# (AsyncSessionLocal, bypassing any FastAPI dependency_overrides), so there
# is no way to roll back its write inside a test transaction the way
# test_api_endpoints.py's `api` fixture does for request-scoped writes;
# these tests leave real (small, clearly-labeled) rows in analytics.ml_models
# and small joblib artifacts under backend/artifacts/ml/, matching how the
# rest of this session's live-verification scripts operate.
#
# ONE TEST FUNCTION for anything that touches the database (JUDGMENT CALL,
# flagged): AsyncSessionLocal's engine (infrastructure/database.py) is a
# process-lifetime singleton bound to whichever event loop first uses it —
# fine for a real uvicorn process (one loop, forever), but pytest-asyncio
# gives EACH test function its own fresh event loop by default, and the
# second DB-touching test in a module reliably hits "Event loop is closed" /
# a dead proactor transport reusing the same global engine across two
# different loops. conftest.py's db_session fixture avoids this by building
# a brand-new engine per test — not an option here since the background
# task calls AsyncSessionLocal() directly, bypassing fixture injection
# entirely. Consolidating every DB-touching assertion into one test keeps
# everything on one event loop without fighting pytest-asyncio's scope
# config; the pure-validation tests below (400/404, no DB writes) stay
# separate since they never touch the engine.
from __future__ import annotations

import asyncio
import random

import pytest
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis

from quant_hub.config import settings
from quant_hub.infrastructure.cache import get_redis
from quant_hub.main import app


@pytest.fixture
async def client():
    # Same root cause as the module docstring above, for Redis specifically:
    # the global redis_pool (infrastructure/cache.py) is bound to whichever
    # event loop first uses it; a fresh per-test client (reachable via
    # dependency_overrides, unlike the DB session) sidesteps it.
    fresh_redis = Redis.from_url(settings.redis_url, decode_responses=True)
    app.dependency_overrides[get_redis] = lambda: fresh_redis
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_redis, None)
        await fresh_redis.aclose()


def _classification_dataset(n: int = 40, seed: int = 0):
    rng = random.Random(seed)
    features = [[rng.gauss(0, 1) for _ in range(4)] for _ in range(n)]
    targets = [1 if sum(row) > 0 else 0 for row in features]
    return features, targets


async def _wait_for_completion(client: AsyncClient, job_id: str, timeout_s: float = 15.0) -> dict:
    elapsed = 0.0
    while elapsed < timeout_s:
        resp = await client.get(f"/api/ml/train/{job_id}/status")
        data = resp.json()["data"]
        if data["status"] in ("COMPLETED", "FAILED"):
            return data
        await asyncio.sleep(0.3)
        elapsed += 0.3
    raise TimeoutError(f"job {job_id} did not complete in {timeout_s}s")


@pytest.mark.asyncio
async def test_train_unknown_model_type_rejected(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/ml/train",
        json={"model_type": "NotARealModel", "feature_data": [[1.0]], "target_data": [1.0]},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_train_empty_data_rejected(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/ml/train",
        json={"model_type": "XGBoost_MetaLabeler", "feature_data": [], "target_data": []},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_train_status_unknown_job_404(client: AsyncClient) -> None:
    resp = await client.get("/api/ml/train/nonexistent-job-id/status")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_predict_unknown_model_type_rejected(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/ml/predict",
        json={"model_type": "NotARealModel", "feature_data": [[1.0]]},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_train_then_predict_end_to_end(client: AsyncClient) -> None:
    # A model_type unlikely to have been deployed by an earlier run — real
    # 404 before any training has happened for it.
    before_resp = await client.post(
        "/api/ml/predict",
        json={"model_type": "LSTM_Predictor", "feature_data": [[0.1, 0.2, 0.3]]},
    )
    assert before_resp.status_code in (200, 404)  # 200 only if a prior run already deployed one

    features, targets = _classification_dataset(seed=1)
    train_resp = await client.post(
        "/api/ml/train",
        json={
            "model_type": "XGBoost_MetaLabeler",
            "hyperparams": {"n_estimators": 20},
            "feature_data": features,
            "target_data": targets,
        },
    )
    assert train_resp.status_code == 202
    job_id = train_resp.json()["data"]["job_id"]

    completed = await _wait_for_completion(client, job_id)
    assert completed["status"] == "COMPLETED"
    assert completed["model_type"] == "XGBoost_MetaLabeler"
    assert 0.0 <= completed["metrics"]["accuracy"] <= 1.0
    assert "feature_importance" in completed["metrics"]

    predict_resp = await client.post(
        "/api/ml/predict",
        json={"model_type": "XGBoost_MetaLabeler", "feature_data": features[:3]},
    )
    assert predict_resp.status_code == 200
    data = predict_resp.json()["data"]
    assert len(data["predictions"]) == 3
    assert data["probabilities"] == data["predictions"]
    for p, c in zip(data["probabilities"], data["confidence"]):
        assert 0.0 <= p <= 1.0
        assert c == max(p, 1 - p)

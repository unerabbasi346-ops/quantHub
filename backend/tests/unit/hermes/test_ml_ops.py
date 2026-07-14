# Unit tests for hermes/monitors/ml_ops.py — DB/Redis mocked, no live
# connections.
from __future__ import annotations

import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from quant_hub.hermes.monitors.ml_ops import get_active_training_jobs, get_model_registry


def _session_returning(rows: list) -> AsyncMock:
    session = AsyncMock()
    result = MagicMock()
    result.all.return_value = rows
    session.execute = AsyncMock(return_value=result)
    return session


@pytest.mark.asyncio
async def test_model_registry_extracts_numeric_accuracy() -> None:
    now = datetime.now(timezone.utc)
    rows = [
        SimpleNamespace(
            id="m1", name="XGBoost_MetaLabeler", model_type="XGBoost_MetaLabeler", status="DEPLOYED",
            metrics={"accuracy": 0.87, "precision": 0.9}, deployed_at=now, created_at=now,
        ),
        SimpleNamespace(
            id="m2", name="HMM_RegimeDetector", model_type="HMM_RegimeDetector", status="DRAFT",
            metrics=None, deployed_at=None, created_at=now,
        ),
        SimpleNamespace(
            id="m3", name="bad-metrics", model_type="LSTM_Predictor", status="DRAFT",
            metrics={"accuracy": "not-a-number"}, deployed_at=None, created_at=now,
        ),
    ]
    session = _session_returning(rows)

    result = await get_model_registry(session)

    by_id = {m.model_id: m for m in result}
    assert by_id["m1"].accuracy == pytest.approx(0.87)
    assert by_id["m2"].accuracy is None
    assert by_id["m3"].accuracy is None  # non-numeric metrics value never coerced


@pytest.mark.asyncio
async def test_active_training_jobs_excludes_completed_and_failed() -> None:
    payloads = {
        "ml:train:job-running": {"status": "RUNNING", "model_type": "XGBoost_MetaLabeler", "created_at": "t1"},
        "ml:train:job-pending": {"status": "PENDING", "model_type": "LSTM_Predictor", "created_at": "t2"},
        "ml:train:job-done": {"status": "COMPLETED", "model_type": "XGBoost_MetaLabeler", "created_at": "t3", "completed_at": "t4"},
        "ml:train:job-failed": {"status": "FAILED", "model_type": "HMM_RegimeDetector", "created_at": "t5", "completed_at": "t6"},
    }

    async def fake_scan_iter(match: str):
        for key in payloads:
            yield key

    redis = AsyncMock()
    redis.scan_iter = fake_scan_iter
    redis.get = AsyncMock(side_effect=lambda key: json.dumps(payloads[key]))

    result = await get_active_training_jobs(redis)

    job_ids = {j.job_id for j in result}
    assert job_ids == {"job-running", "job-pending"}

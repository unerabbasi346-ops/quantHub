# Governing specification: Doc 09 — Database Architecture (analytics.ml_models,
#   initial schema migration c3a8f2b91e4d — this table has existed since Step
#   1.1 but had no real write/read path until this feature).
# Layer: Domain — Doc 07 §Layers (value objects; no persistence, no I/O)
# Per Doc 00 §14.11
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class TrainedModelRecord:
    """A persisted analytics.ml_models row — one completed training run's
    governed artifact record. `artifact_path` points at the joblib file
    model_factory-created models are saved to; `config` is the hyperparams
    the model was trained with; `metrics` is the model's own evaluate()
    output (accuracy/precision/rmse/etc., varies by model_type).

    JUDGMENT CALL (Doc 00 §14.5/§14.7, flagged): `status` is set to
    'DEPLOYED' immediately on successful training completion (this schema's
    only other documented status besides the DRAFT default) — there is no
    separate promotion/approval workflow anywhere in this codebase, so
    auto-deploying the newly-trained model is the only way `/predict` can
    ever find a model to serve. A real governed promotion gate is out of
    scope for this task.
    """

    id: UUID
    name: str
    version: str
    status: str
    model_type: str
    framework: str
    artifact_path: str
    config: Mapping[str, Any]
    metrics: Mapping[str, Any] | None
    deployed_at: datetime | None
    created_at: datetime

# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
#                          Doc 09 — Database Architecture (analytics.ml_models)
# Layer: Domain — Doc 07 §Layers
# Per Doc 00 §14.11
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any
from uuid import UUID

from quant_hub.domain.ml.entities import TrainedModelRecord


class MLModelRepository(ABC):
    """Persistence contract for analytics.ml_models — Doc 09.

    Table existed since the initial schema (migration c3a8f2b91e4d) with no
    real write/read path until this feature. Does not commit (caller owns
    the transaction boundary, Doc 07 §Implementation Rules).
    """

    @abstractmethod
    async def register_trained(
        self,
        *,
        model_type: str,
        version: str,
        framework: str,
        artifact_path: str,
        config: Mapping[str, Any],
        metrics: Mapping[str, Any] | None,
    ) -> UUID:
        """Register a newly-completed training run as a DEPLOYED model
        (see TrainedModelRecord's docstring for the auto-deploy judgment
        call). `name` is set to `model_type` — this platform trains one
        model per model_type at a time, versioned by the training job id.
        """
        ...

    @abstractmethod
    async def get_latest_deployed(self, model_type: str) -> TrainedModelRecord | None:
        """The most recently DEPLOYED model of `model_type`, or None if
        none has ever completed training — the /predict and signal-
        enrichment lookup.
        """
        ...

# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
#                          Doc 09 — Database Architecture (analytics.ml_models)
# Layer: Persistence — Doc 07 §Layers
# Per Doc 00 §14.11
from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any
from uuid import UUID

from sqlalchemy import text

from quant_hub.domain.ml.entities import TrainedModelRecord
from quant_hub.domain.ml.interfaces import MLModelRepository
from quant_hub.persistence.repositories.base import BaseRepository


def _row_to_record(row: object) -> TrainedModelRecord:
    return TrainedModelRecord(
        id=row["id"],
        name=row["name"],
        version=row["version"],
        status=row["status"],
        model_type=row["model_type"],
        framework=row["framework"],
        artifact_path=row["artifact_path"],
        config=row["config"] or {},
        metrics=row["metrics"],
        deployed_at=row["deployed_at"],
        created_at=row["created_at"],
    )


class SQLAlchemyMLModelRepository(BaseRepository[object], MLModelRepository):
    """Concrete repository for analytics.ml_models."""

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
        stmt = text(
            """
            INSERT INTO analytics.ml_models
                (name, version, status, model_type, framework, artifact_path,
                 config, metrics, deployed_at)
            VALUES
                (:name, :version, 'DEPLOYED', :model_type, :framework, :artifact_path,
                 CAST(:config AS JSONB), CAST(:metrics AS JSONB), clock_timestamp())
            RETURNING id
            """
        )
        result = await self._session.execute(
            stmt,
            {
                "name": model_type,
                "version": version,
                "model_type": model_type,
                "framework": framework,
                "artifact_path": artifact_path,
                "config": json.dumps(dict(config)),
                "metrics": json.dumps(dict(metrics)) if metrics is not None else None,
            },
        )
        return result.scalar_one()

    async def get_latest_deployed(self, model_type: str) -> TrainedModelRecord | None:
        result = await self._session.execute(
            text(
                """
                SELECT id, name, version, status, model_type, framework, artifact_path,
                       config, metrics, deployed_at, created_at
                FROM analytics.ml_models
                WHERE model_type = :model_type AND status = 'DEPLOYED'
                ORDER BY deployed_at DESC
                LIMIT 1
                """
            ),
            {"model_type": model_type},
        )
        row = result.mappings().one_or_none()
        return None if row is None else _row_to_record(row)

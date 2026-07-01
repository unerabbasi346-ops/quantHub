# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Persistence — Doc 07 §Layers
# Repository pattern — Doc 07 §Implementation Rules
# Per Doc 00 §14.11
from __future__ import annotations

from uuid import UUID

from quant_hub.domain.research.interfaces import ExperimentRepository, ResearchProjectRepository
from quant_hub.persistence.repositories.base import BaseRepository


class SQLAlchemyResearchProjectRepository(BaseRepository[object], ResearchProjectRepository):
    """Concrete repository for analytics.research_projects."""

    async def get_by_id(self, project_id: UUID) -> object | None:
        return None  # stub

    async def list_by_owner(self, owner_id: UUID) -> list[object]:
        return []  # stub


class SQLAlchemyExperimentRepository(BaseRepository[object], ExperimentRepository):
    """Concrete repository for analytics.experiments."""

    async def get_by_project(self, project_id: UUID) -> list[object]:
        return []  # stub

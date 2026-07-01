# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Domain — Doc 07 §Layers
# Service: Research — Doc 07 §Core Services
# Per Doc 00 §14.11
from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID


class ResearchProjectRepository(ABC):
    """Persistence contract for analytics.research_projects — Doc 07 §Implementation Rules."""

    @abstractmethod
    async def get_by_id(self, project_id: UUID) -> object | None: ...

    @abstractmethod
    async def list_by_owner(self, owner_id: UUID) -> list[object]: ...


class ExperimentRepository(ABC):
    """Persistence contract for analytics.experiments — Doc 07 §Implementation Rules."""

    @abstractmethod
    async def get_by_project(self, project_id: UUID) -> list[object]: ...

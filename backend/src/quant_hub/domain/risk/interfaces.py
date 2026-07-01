# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Domain — Doc 07 §Layers
# Service: Risk — Doc 07 §Core Services
# Per Doc 00 §14.11
from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID


class RiskSnapshotRepository(ABC):
    """Persistence contract for analytics.risk_snapshots — Doc 07 §Implementation Rules."""

    @abstractmethod
    async def get_latest(self, portfolio_id: UUID) -> object | None: ...

    @abstractmethod
    async def save(self, snapshot: object) -> None: ...

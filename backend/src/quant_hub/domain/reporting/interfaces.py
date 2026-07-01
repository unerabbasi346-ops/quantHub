# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Domain — Doc 07 §Layers
# Service: Reporting — Doc 07 §Core Services
# Per Doc 00 §14.11
from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID


class ReportGeneratorInterface(ABC):
    """Contract for report generation — Doc 07 §Implementation Rules."""

    @abstractmethod
    async def generate(self, portfolio_id: UUID, report_type: str) -> bytes: ...

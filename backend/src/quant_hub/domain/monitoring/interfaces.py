# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Domain — Doc 07 §Layers
# Service: Monitoring — Doc 07 §Core Services
# Observability: structured logs, request IDs, execution metrics — Doc 07 §Logging & Observability
# Per Doc 00 §14.11
from __future__ import annotations

from abc import ABC, abstractmethod


class MetricsInterface(ABC):
    """Contract for operational metrics emission — Doc 07 §Logging & Observability."""

    @abstractmethod
    async def record(self, metric_name: str, value: float, labels: dict) -> None: ...

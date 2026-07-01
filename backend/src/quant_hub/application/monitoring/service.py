# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Application — Doc 07 §Layers
# Service: Monitoring — Doc 07 §Core Services
# Observability: structured logs, execution metrics — Doc 07 §Logging & Observability
# Per Doc 00 §14.11
from __future__ import annotations

from quant_hub.domain.monitoring.interfaces import MetricsInterface


class MonitoringService:
    """Application service stub — business logic not implemented in Step 0.4."""

    def __init__(self, metrics: MetricsInterface) -> None:
        self._metrics = metrics

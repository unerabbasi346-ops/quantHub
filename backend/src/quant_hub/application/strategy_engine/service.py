# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Application — Doc 07 §Layers
# Service: Strategy Engine — Doc 07 §Core Services
# P-1: platform never assumes specific strategy; config is opaque
# Per Doc 00 §14.11
from __future__ import annotations

from quant_hub.domain.strategy_engine.interfaces import StrategyRepository


class StrategyEngineService:
    """Application service stub — business logic not implemented in Step 0.4."""

    def __init__(self, repository: StrategyRepository) -> None:
        self._repository = repository

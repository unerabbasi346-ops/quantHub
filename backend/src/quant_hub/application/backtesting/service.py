# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Application — Doc 07 §Layers
# Service: Backtesting — Doc 07 §Core Services
# Background processing: backtests execute asynchronously — Doc 07 §Background Processing
# Per Doc 00 §14.11
from __future__ import annotations

from quant_hub.domain.backtesting.interfaces import BacktestRepository


class BacktestingService:
    """Application service stub — business logic not implemented in Step 0.4.

    Doc 07 §Background Processing: backtest jobs are long-running and execute
    asynchronously; they are observable and retry transient failures.
    """

    def __init__(self, repository: BacktestRepository) -> None:
        self._repository = repository

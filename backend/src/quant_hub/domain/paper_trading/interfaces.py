# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Domain — Doc 07 §Layers
# Service: Paper Trading — Doc 07 §Core Services
# Per Doc 00 §14.11
from __future__ import annotations

from abc import ABC, abstractmethod


class PaperTradingSimulatorInterface(ABC):
    """Contract for paper trading simulation — Doc 07 §Implementation Rules.

    Paper trading shares the Order/Execution/Position schema with live trading
    (distinguished by portfolio_type='PAPER' in core.portfolios).
    No separate persistence table required.
    """

    @abstractmethod
    async def simulate_fill(self, order: object) -> object: ...

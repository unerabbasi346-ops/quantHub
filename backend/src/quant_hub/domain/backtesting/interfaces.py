# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
#                          Doc 14 §10.3 — Backtesting Engine Architecture
# Layer: Domain — Doc 07 §Layers
# Service: Backtesting — Doc 07 §Core Services
# Invariants: P-2 (immutable artifact), P-5 (governed record)
# Per Doc 00 §14.11
from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from quant_hub.domain.backtesting.entities import BacktestConfig, BacktestResult


class BacktestRepository(ABC):
    """Persistence contract for analytics.backtests — Doc 14 §10.3 / Doc 07.

    A backtest is a governed artifact (§10.3.6 Environment Recording, P-5):
    `create`d RUNNING when the replay starts, `complete`d with results when it
    finishes. Implementations do not commit (caller owns the transaction).
    """

    @abstractmethod
    async def create(self, config: BacktestConfig, strategy_id: UUID) -> UUID:
        """Register a RUNNING backtest and return its id (§10.3.3 config recorded)."""
        ...

    @abstractmethod
    async def complete(self, backtest_id: UUID, result: BacktestResult) -> None:
        """Record results and mark the backtest COMPLETED (§10.3.6/§10.3.7)."""
        ...

    @abstractmethod
    async def get_by_id(self, backtest_id: UUID) -> object | None: ...

    @abstractmethod
    async def list_by_strategy(self, strategy_id: UUID) -> list[object]: ...

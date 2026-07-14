# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
#                          Doc 14 §10.3 — Backtesting Engine Architecture
# Layer: Domain — Doc 07 §Layers
# Service: Backtesting — Doc 07 §Core Services
# Invariants: P-2 (immutable artifact), P-5 (governed record)
# Per Doc 00 §14.11
from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from quant_hub.domain.analytics.entities import ComputedMetrics, EquityPoint
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

    # F-21 (migration c7d3f9a2e5b8): the real per-step equity curve and its
    # derived metric suite, closing the gap BacktestResult's docstring flags.
    @abstractmethod
    async def save_equity_curve(self, backtest_id: UUID, points: list[EquityPoint]) -> None:
        """Persist the full per-step equity curve for one completed backtest."""
        ...

    @abstractmethod
    async def save_computed_metrics(self, metrics: ComputedMetrics) -> None:
        """Persist the Doc 14 §10.3.7 metric suite for one completed backtest."""
        ...

    @abstractmethod
    async def get_computed_metrics(self, backtest_id: UUID) -> ComputedMetrics | None: ...

    @abstractmethod
    async def get_latest_completed_by_strategy(self, strategy_id: UUID) -> object | None:
        """Most recently COMPLETED backtest row for `strategy_id`, or None if
        the strategy has no completed backtest — the metrics API's "most
        recent backtest run" lookup.
        """
        ...

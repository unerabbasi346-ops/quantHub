# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Domain — Doc 07 §Layers
# Service: Execution — Doc 07 §Core Services
# Doc 02: Risk Engine must approve every order before routing — mandatory pre-trade gate
# Per Doc 00 §14.11
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from quant_hub.domain.execution.entities import (
    Fill,
    OrderIntent,
    RecordedExecution,
    RecordedOrder,
)


class InvalidOrderTransition(RuntimeError):
    """Raised when an order lifecycle transition is not permitted — Doc 14
    §10.7.4 ("Invalid transitions shall be rejected").

    The persistence layer guards each transition with UPDATE ... WHERE
    status = <expected>; a zero-row result means the order was not in the
    required prior state (or does not exist), and this is raised rather than
    silently no-op'ing.
    """


@dataclass(frozen=True)
class RiskDecision:
    """Outcome of a pre-trade risk check — Doc 02 §Risk Gate."""

    approved: bool
    reason: str = ""


class RiskApprovalInterface(ABC):
    """Mandatory pre-trade risk gate — Doc 02: Risk Engine approves every order.

    Defined here (execution domain) because the execution service is the
    consumer. The risk domain implements this contract, satisfying
    Doc 07 §Dependency Rules: infrastructure implements domain interfaces.

    A concrete stub that always approves is provided in
    infrastructure/risk_approval.py for use until real risk logic is wired.
    """

    @abstractmethod
    async def evaluate(self, order: object) -> RiskDecision: ...


class OrderRepository(ABC):
    """Persistence contract for core.orders — Doc 07 §Implementation Rules."""

    @abstractmethod
    async def create(self, intent: OrderIntent, asset_id: UUID) -> RecordedOrder:
        """Persist a computed OrderIntent as a CREATED order (Step 3.3).

        `asset_id` is passed resolved (AssetRef -> market_data.assets.id) by
        the caller, mirroring SignalRepository.record(strategy_id, asset_id,
        signal, ...) — the repository does not perform cross-table symbol
        resolution. The first real core.orders write in the platform.
        """
        ...

    @abstractmethod
    async def get_by_id(self, order_id: UUID) -> RecordedOrder | None: ...

    @abstractmethod
    async def get_by_idempotency_key(self, key: UUID) -> RecordedOrder | None: ...

    @abstractmethod
    async def list_by_portfolio(
        self, portfolio_id: UUID, limit: int | None = None
    ) -> list[RecordedOrder]:
        """Orders for `portfolio_id`, oldest-first (created_at, id).

        Return type tightened from `list[object]` to `list[RecordedOrder]` in
        Step 4.4, its first real consumer (GET /v1/portfolios/{id}/orders — the
        blotter). The concrete impl already returned RecordedOrder; the
        contract now says so.

        `limit`, when given, caps the result to the most recent N orders
        (still returned oldest-first).
        """
        ...

    @abstractmethod
    async def list_by_strategy(
        self, strategy_id: UUID, limit: int | None = None
    ) -> list[RecordedOrder]:
        """Orders for `strategy_id`, oldest-first — the Execution page's
        strategy-selector feed (GET /v1/strategies/{id}/orders). Filters on
        core.orders.strategy_id directly (real FK lineage) rather than routing
        through the strategy's own portfolio_id, which is unset for every
        currently-registered strategy.

        `limit`, when given, caps the result to the most recent N orders
        (still returned oldest-first).
        """
        ...

    # Order lifecycle transitions — Doc 14 §10.7.4. Each guards the prior
    # state and raises InvalidOrderTransition on a disallowed transition.
    @abstractmethod
    async def mark_validated(self, order_id: UUID) -> RecordedOrder:
        """CREATED -> VALIDATED (order passed pre-trade risk, §10.7.5)."""
        ...

    @abstractmethod
    async def mark_rejected(self, order_id: UUID) -> RecordedOrder:
        """CREATED -> REJECTED (pre-trade risk rejected the order, §10.7.5).

        The human-readable reason is recorded in analytics.risk_assessments
        (linked by order_id, Step 3.4), so §10.7.5's "rejection reason shall
        be recorded ... not silently swallowed" is satisfied without a
        redundant column on core.orders.
        """
        ...

    @abstractmethod
    async def mark_filled(
        self, order_id: UUID, filled_quantity: Decimal, average_price: Decimal
    ) -> RecordedOrder:
        """VALIDATED -> FILLED (simulated fill complete, §10.8.6/§10.7.4)."""
        ...


class ExecutionRepository(ABC):
    """Persistence contract for core.executions — Doc 07 §Implementation Rules."""

    @abstractmethod
    async def record(
        self,
        fill: Fill,
        realized_pnl: Decimal,
        *,
        price_return_pct: Decimal | None = None,
        market_move_pct: Decimal | None = None,
        exit_reason: str | None = None,
    ) -> RecordedExecution:
        """Persist a Fill as an immutable core.executions row — §10.9.4.

        `realized_pnl` is the PositionUpdate.realized_pnl this fill produced
        (domain/portfolio/positions.py::apply_fill_to_position) — computed by
        the caller BEFORE this call (it needs the pre-fill position state),
        then persisted onto the trade record it belongs to (migration
        a2e4c7b1d6f9).

        `price_return_pct`/`market_move_pct`/`exit_reason` (backtest TP/SL
        step, migration <trade_result>): supplied ONLY by the backtest engine
        on a trade's CLOSING fill — None everywhere else (a live/paper fill,
        or a backtest's own entry fill), matching RecordedExecution's docstring.
        """
        ...

    @abstractmethod
    async def get_by_order(self, order_id: UUID) -> list[RecordedExecution]: ...

    @abstractmethod
    async def list_by_portfolio(self, portfolio_id: UUID) -> list[RecordedExecution]:
        """All executions for `portfolio_id`, oldest-first — batch feed for
        the Execution page (avoids an N+1 get_by_order call per order).
        """
        ...

    @abstractmethod
    async def list_by_strategy(
        self, strategy_id: UUID, limit: int | None = None
    ) -> list[RecordedExecution]:
        """Executions whose order was generated by `strategy_id`, oldest-first
        — joins through core.orders.strategy_id since core.executions itself
        carries no strategy_id column.

        `limit`, when given, caps the result to the most recent N executions
        (still returned oldest-first).
        """
        ...

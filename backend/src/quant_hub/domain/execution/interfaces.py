# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Domain — Doc 07 §Layers
# Service: Execution — Doc 07 §Core Services
# Doc 02: Risk Engine must approve every order before routing — mandatory pre-trade gate
# Per Doc 00 §14.11
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID

from quant_hub.domain.execution.entities import OrderIntent, RecordedOrder


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
    async def list_by_portfolio(self, portfolio_id: UUID) -> list[object]: ...


class ExecutionRepository(ABC):
    """Persistence contract for core.executions — Doc 07 §Implementation Rules."""

    @abstractmethod
    async def get_by_order(self, order_id: UUID) -> list[object]: ...

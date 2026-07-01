# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Persistence — Doc 07 §Layers
# Repository pattern — Doc 07 §Implementation Rules
# Per Doc 00 §14.11
from __future__ import annotations

from uuid import UUID

from quant_hub.domain.execution.interfaces import ExecutionRepository, OrderRepository
from quant_hub.persistence.repositories.base import BaseRepository


class SQLAlchemyOrderRepository(BaseRepository[object], OrderRepository):
    """Concrete repository for core.orders."""

    async def get_by_id(self, order_id: UUID) -> object | None:
        return None  # stub

    async def get_by_idempotency_key(self, key: UUID) -> object | None:
        return None  # stub

    async def list_by_portfolio(self, portfolio_id: UUID) -> list[object]:
        return []  # stub


class SQLAlchemyExecutionRepository(BaseRepository[object], ExecutionRepository):
    """Concrete repository for core.executions."""

    async def get_by_order(self, order_id: UUID) -> list[object]:
        return []  # stub

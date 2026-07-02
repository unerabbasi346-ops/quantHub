# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Persistence — Doc 07 §Layers
# Repository pattern — Doc 07 §Implementation Rules
# Doc 14 §10.7.3 Order Model; §10.7.4 Order Lifecycle (CREATED); §10.7.5 idempotency
# Per Doc 00 §14.11
#
# SQLAlchemyOrderRepository (Step 3.3): the first real core.orders write.
# Raw-SQL-first via sqlalchemy.text(), same approach as market_data.py /
# strategy_engine.py (no ORM models; target_metadata=None in env.py, Doc 09
# §Migration Strategy). Never commits — the caller owns the transaction
# boundary (Doc 07 §Implementation Rules), same convention as every other
# repository. Writes against the Step 1.1 schema with quantity now NUMERIC(28,8)
# (Step 3.0, F-1..F-4 / F-11) and a dedicated signal_id column (F-13
# resolution, migration d1f8b6c4a7e2) for signal lineage.
from __future__ import annotations

from uuid import UUID

from sqlalchemy import text

from quant_hub.domain.execution.entities import (
    OrderIntent,
    OrderSide,
    OrderStatus,
    OrderType,
    RecordedOrder,
    TimeInForce,
)
from quant_hub.domain.execution.interfaces import ExecutionRepository, OrderRepository
from quant_hub.persistence.repositories.base import BaseRepository


def _row_to_order(row: object) -> RecordedOrder:
    return RecordedOrder(
        id=row["id"],
        idempotency_key=row["idempotency_key"],
        portfolio_id=row["portfolio_id"],
        strategy_id=row["strategy_id"],
        asset_id=row["asset_id"],
        side=OrderSide(row["side"]),
        quantity=row["quantity"],
        order_type=OrderType(row["order_type"]),
        time_in_force=TimeInForce(row["time_in_force"]),
        status=OrderStatus(row["status"]),
        signal_id=row["signal_id"],
        created_at=row["created_at"],
    )


class SQLAlchemyOrderRepository(BaseRepository[object], OrderRepository):
    """Concrete repository for core.orders — Step 3.3, Doc 14 §10.7."""

    async def create(self, intent: OrderIntent, asset_id: UUID) -> RecordedOrder:
        """Append a CREATED order (§10.7.4). Plain INSERT — no ON CONFLICT.

        Idempotency (§10.7.5, judgment call flagged): the `idempotency_key`
        column is UNIQUE (Step 1.1 schema); this method relies on that unique
        constraint to reject a genuine duplicate at the DB level. It does NOT
        implement §10.7.5's full "duplicate -> return original order state"
        client-retry protocol (24h window, key-rotation-on-modify) — that is
        Order Management Service machinery deferred per S-5. Each generation
        call mints a fresh UUID v7 key (application layer), so no natural
        duplicate arises in this step's flow; a real retry with a colliding
        key would surface as an IntegrityError to the caller rather than
        silently returning the prior order.

        `signal_id` is written to its own FK-enforced column (F-13 resolution,
        migration d1f8b6c4a7e2) — REFERENCES core.signals(id), nullable.
        `correlation_id` is deliberately left NULL/untouched here: it is not
        this repository's concern, reserved for its own established platform
        meaning (request/event tracing, Doc 10 §6/§8). `status` takes the
        schema DEFAULT 'CREATED'; limit_price/stop_price stay NULL (MARKET
        only, S-5). Does not commit.
        """
        stmt = text(
            """
            INSERT INTO core.orders
                (idempotency_key, signal_id, portfolio_id, strategy_id, asset_id,
                 order_type, side, quantity, time_in_force)
            VALUES
                (:idempotency_key, :signal_id, :portfolio_id, :strategy_id, :asset_id,
                 :order_type, :side, :quantity, :time_in_force)
            RETURNING id, idempotency_key, portfolio_id, strategy_id, asset_id,
                      order_type, side, quantity, time_in_force, status,
                      signal_id, created_at
            """
        )
        result = await self._session.execute(
            stmt,
            {
                "idempotency_key": intent.idempotency_key,
                "signal_id": intent.signal_id,
                "portfolio_id": intent.portfolio_id,
                "strategy_id": intent.strategy_id,
                "asset_id": asset_id,
                "order_type": intent.order_type.value,
                "side": intent.side.value,
                "quantity": intent.quantity,
                "time_in_force": intent.time_in_force.value,
            },
        )
        return _row_to_order(result.mappings().one())

    async def get_by_id(self, order_id: UUID) -> RecordedOrder | None:
        result = await self._session.execute(
            text(
                """
                SELECT id, idempotency_key, portfolio_id, strategy_id, asset_id,
                       order_type, side, quantity, time_in_force, status,
                       signal_id, created_at
                FROM core.orders
                WHERE id = :id
                """
            ),
            {"id": order_id},
        )
        row = result.mappings().one_or_none()
        return None if row is None else _row_to_order(row)

    async def get_by_idempotency_key(self, key: UUID) -> RecordedOrder | None:
        result = await self._session.execute(
            text(
                """
                SELECT id, idempotency_key, portfolio_id, strategy_id, asset_id,
                       order_type, side, quantity, time_in_force, status,
                       signal_id, created_at
                FROM core.orders
                WHERE idempotency_key = :key
                """
            ),
            {"key": key},
        )
        row = result.mappings().one_or_none()
        return None if row is None else _row_to_order(row)

    async def list_by_portfolio(self, portfolio_id: UUID) -> list[object]:
        result = await self._session.execute(
            text(
                """
                SELECT id, idempotency_key, portfolio_id, strategy_id, asset_id,
                       order_type, side, quantity, time_in_force, status,
                       signal_id, created_at
                FROM core.orders
                WHERE portfolio_id = :portfolio_id
                ORDER BY created_at
                """
            ),
            {"portfolio_id": portfolio_id},
        )
        return [_row_to_order(row) for row in result.mappings().all()]


class SQLAlchemyExecutionRepository(BaseRepository[object], ExecutionRepository):
    """Concrete repository for core.executions — Step 3.5 (not yet implemented)."""

    async def get_by_order(self, order_id: UUID) -> list[object]:
        return []  # stub — Execution (Step 3.5, §10.8/§10.9) not yet built

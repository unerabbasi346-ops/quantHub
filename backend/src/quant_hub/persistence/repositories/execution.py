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

from decimal import ROUND_HALF_EVEN, Decimal
from uuid import UUID

from sqlalchemy import text

from quant_hub.domain.execution.entities import (
    Fill,
    OrderIntent,
    OrderSide,
    OrderStatus,
    OrderType,
    RecordedExecution,
    RecordedOrder,
    TimeInForce,
)
from quant_hub.domain.execution.interfaces import (
    ExecutionRepository,
    InvalidOrderTransition,
    OrderRepository,
)
from quant_hub.persistence.repositories.base import BaseRepository

# The single core.orders projection every read/RETURNING uses, so the column
# set and _row_to_order never drift. Includes the fill-outcome columns
# (filled_quantity, average_price) surfaced to RecordedOrder in Step 4.4.
_ORDER_COLS = (
    "id, idempotency_key, portfolio_id, strategy_id, asset_id, "
    "order_type, side, quantity, filled_quantity, average_price, "
    "time_in_force, status, signal_id, created_at"
)
_NET_SCALE = Decimal("0.0001")  # core.executions.net_amount NUMERIC(20,4)


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
        filled_quantity=row["filled_quantity"],
        average_price=row["average_price"],
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
            f"""
            INSERT INTO core.orders
                (idempotency_key, signal_id, portfolio_id, strategy_id, asset_id,
                 order_type, side, quantity, time_in_force)
            VALUES
                (:idempotency_key, :signal_id, :portfolio_id, :strategy_id, :asset_id,
                 :order_type, :side, :quantity, :time_in_force)
            RETURNING {_ORDER_COLS}
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
            text(f"SELECT {_ORDER_COLS} FROM core.orders WHERE id = :id"),
            {"id": order_id},
        )
        row = result.mappings().one_or_none()
        return None if row is None else _row_to_order(row)

    async def get_by_idempotency_key(self, key: UUID) -> RecordedOrder | None:
        result = await self._session.execute(
            text(f"SELECT {_ORDER_COLS} FROM core.orders WHERE idempotency_key = :key"),
            {"key": key},
        )
        row = result.mappings().one_or_none()
        return None if row is None else _row_to_order(row)

    async def list_by_portfolio(
        self, portfolio_id: UUID, limit: int | None = None
    ) -> list[RecordedOrder]:
        # Ordered (created_at, id) for a stable, deterministic blotter feed —
        # id breaks ties when two orders share a created_at (Step 4.4).
        # `limit` caps to the most recent N (perf: portfolios can carry 40k+
        # orders — unbounded fetch was shipping the whole table to the
        # dashboard on every poll). DESC+LIMIT then reverse keeps the
        # oldest-first contract callers rely on.
        if limit is not None:
            result = await self._session.execute(
                text(
                    f"""
                    SELECT {_ORDER_COLS}
                    FROM core.orders
                    WHERE portfolio_id = :portfolio_id
                    ORDER BY created_at DESC, id DESC
                    LIMIT :limit
                    """
                ),
                {"portfolio_id": portfolio_id, "limit": limit},
            )
            rows = list(reversed(result.mappings().all()))
        else:
            result = await self._session.execute(
                text(
                    f"""
                    SELECT {_ORDER_COLS}
                    FROM core.orders
                    WHERE portfolio_id = :portfolio_id
                    ORDER BY created_at, id
                    """
                ),
                {"portfolio_id": portfolio_id},
            )
            rows = result.mappings().all()
        return [_row_to_order(row) for row in rows]

    async def list_by_strategy(
        self, strategy_id: UUID, limit: int | None = None
    ) -> list[RecordedOrder]:
        # Same unbounded-fetch perf issue as list_by_portfolio (a strategy can
        # carry 40k+ backtest orders) — same DESC+LIMIT+reverse fix.
        if limit is not None:
            result = await self._session.execute(
                text(
                    f"""
                    SELECT {_ORDER_COLS}
                    FROM core.orders
                    WHERE strategy_id = :strategy_id
                    ORDER BY created_at DESC, id DESC
                    LIMIT :limit
                    """
                ),
                {"strategy_id": strategy_id, "limit": limit},
            )
            rows = list(reversed(result.mappings().all()))
        else:
            result = await self._session.execute(
                text(
                    f"""
                    SELECT {_ORDER_COLS}
                    FROM core.orders
                    WHERE strategy_id = :strategy_id
                    ORDER BY created_at, id
                    """
                ),
                {"strategy_id": strategy_id},
            )
            rows = result.mappings().all()
        return [_row_to_order(row) for row in rows]

    async def _transition(
        self,
        order_id: UUID,
        expected: OrderStatus,
        new_status: OrderStatus,
        extra_sets: str = "",
        extra_params: dict | None = None,
    ) -> RecordedOrder:
        """Guarded lifecycle transition — Doc 14 §10.7.4. UPDATE only if the
        order is in `expected`; a zero-row result raises InvalidOrderTransition
        ("Invalid transitions shall be rejected"). updated_at via
        clock_timestamp() (not NOW(), which is frozen at transaction start —
        same reasoning as the strategy/market_data upserts). Does not commit.
        """
        stmt = text(
            f"""
            UPDATE core.orders
            SET status = :new_status, updated_at = clock_timestamp(){extra_sets}
            WHERE id = :order_id AND status = :expected
            RETURNING {_ORDER_COLS}
            """
        )
        params = {
            "order_id": order_id,
            "expected": expected.value,
            "new_status": new_status.value,
            **(extra_params or {}),
        }
        row = (await self._session.execute(stmt, params)).mappings().one_or_none()
        if row is None:
            raise InvalidOrderTransition(
                f"order {order_id} is not in {expected.value}; "
                f"cannot transition to {new_status.value}"
            )
        return _row_to_order(row)

    async def mark_validated(self, order_id: UUID) -> RecordedOrder:
        return await self._transition(order_id, OrderStatus.CREATED, OrderStatus.VALIDATED)

    async def mark_rejected(self, order_id: UUID) -> RecordedOrder:
        return await self._transition(order_id, OrderStatus.CREATED, OrderStatus.REJECTED)

    async def mark_filled(
        self, order_id: UUID, filled_quantity: Decimal, average_price: Decimal
    ) -> RecordedOrder:
        return await self._transition(
            order_id,
            OrderStatus.VALIDATED,
            OrderStatus.FILLED,
            extra_sets=(
                ", filled_quantity = :filled_quantity, average_price = :average_price, "
                "filled_at = clock_timestamp()"
            ),
            extra_params={"filled_quantity": filled_quantity, "average_price": average_price},
        )


def _row_to_execution(row: object) -> RecordedExecution:
    return RecordedExecution(
        id=row["id"],
        order_id=row["order_id"],
        portfolio_id=row["portfolio_id"],
        asset_id=row["asset_id"],
        side=OrderSide(row["side"]),
        quantity=row["quantity"],
        price=row["price"],
        commission=row["commission"],
        net_amount=row["net_amount"],
        venue=row["venue"],
        executed_at=row["executed_at"],
        created_at=row["created_at"],
        realized_pnl=row["realized_pnl"],
        price_return_pct=row["price_return_pct"],
        market_move_pct=row["market_move_pct"],
        exit_reason=row["exit_reason"],
    )


class SQLAlchemyExecutionRepository(BaseRepository[object], ExecutionRepository):
    """Concrete repository for core.executions — Step 3.5, Doc 14 §10.9.4.

    Append-only immutable trade record per P-2/§10.9.4. Does not commit
    (caller owns the transaction boundary).
    """

    async def record(
        self,
        fill: Fill,
        realized_pnl: Decimal,
        *,
        price_return_pct: Decimal | None = None,
        market_move_pct: Decimal | None = None,
        exit_reason: str | None = None,
    ) -> RecordedExecution:
        """Persist a simulated Fill as a core.executions row.

        `net_amount` is the signed cash effect (§10.9.4): BUY is cash out
        (negative), SELL is cash in (positive), commission included. Quantized
        to the column scale NUMERIC(20,4). `realized_pnl` (migration
        a2e4c7b1d6f9) is the caller-computed PositionUpdate.realized_pnl for
        this fill — already quantized to NUMERIC(20,4) by apply_fill_to_position.
        `price_return_pct`/`market_move_pct`/`exit_reason` are None on every
        entry fill and every live/paper fill — supplied only by the backtest
        engine on a trade's closing fill.
        """
        gross = fill.quantity * fill.price
        if fill.side is OrderSide.BUY:
            net_amount = -(gross + fill.commission)
        else:
            net_amount = gross - fill.commission
        net_amount = net_amount.quantize(_NET_SCALE, rounding=ROUND_HALF_EVEN)

        stmt = text(
            """
            INSERT INTO core.executions
                (order_id, portfolio_id, asset_id, side, quantity, price,
                 commission, net_amount, venue, executed_at, realized_pnl,
                 price_return_pct, market_move_pct, exit_reason)
            VALUES
                (:order_id, :portfolio_id, :asset_id, :side, :quantity, :price,
                 :commission, :net_amount, :venue, :executed_at, :realized_pnl,
                 :price_return_pct, :market_move_pct, :exit_reason)
            RETURNING id, order_id, portfolio_id, asset_id, side, quantity, price,
                      commission, net_amount, venue, executed_at, created_at, realized_pnl,
                      price_return_pct, market_move_pct, exit_reason
            """
        )
        result = await self._session.execute(
            stmt,
            {
                "order_id": fill.order_id,
                "portfolio_id": fill.portfolio_id,
                "asset_id": fill.asset_id,
                "side": fill.side.value,
                "quantity": fill.quantity,
                "price": fill.price,
                "commission": fill.commission,
                "net_amount": net_amount,
                "venue": fill.venue,
                "executed_at": fill.executed_at,
                "realized_pnl": realized_pnl,
                "price_return_pct": price_return_pct,
                "market_move_pct": market_move_pct,
                "exit_reason": exit_reason,
            },
        )
        return _row_to_execution(result.mappings().one())

    async def get_by_order(self, order_id: UUID) -> list[RecordedExecution]:
        result = await self._session.execute(
            text(
                """
                SELECT id, order_id, portfolio_id, asset_id, side, quantity, price,
                       commission, net_amount, venue, executed_at, created_at, realized_pnl,
                       price_return_pct, market_move_pct, exit_reason
                FROM core.executions
                WHERE order_id = :order_id
                ORDER BY executed_at, id
                """
            ),
            {"order_id": order_id},
        )
        return [_row_to_execution(row) for row in result.mappings().all()]

    async def list_by_portfolio(self, portfolio_id: UUID) -> list[RecordedExecution]:
        """All executions for `portfolio_id`, oldest-first — the Execution
        page's batch feed (avoids an N+1 get_by_order call per order).
        """
        result = await self._session.execute(
            text(
                """
                SELECT id, order_id, portfolio_id, asset_id, side, quantity, price,
                       commission, net_amount, venue, executed_at, created_at, realized_pnl,
                       price_return_pct, market_move_pct, exit_reason
                FROM core.executions
                WHERE portfolio_id = :portfolio_id
                ORDER BY executed_at, id
                """
            ),
            {"portfolio_id": portfolio_id},
        )
        return [_row_to_execution(row) for row in result.mappings().all()]

    async def list_by_strategy(
        self, strategy_id: UUID, limit: int | None = None
    ) -> list[RecordedExecution]:
        # Same unbounded-fetch perf issue as the order repos — a strategy can
        # carry 40k+ backtest fills.
        if limit is not None:
            result = await self._session.execute(
                text(
                    """
                    SELECT e.id, e.order_id, e.portfolio_id, e.asset_id, e.side, e.quantity,
                           e.price, e.commission, e.net_amount, e.venue, e.executed_at,
                           e.created_at, e.realized_pnl,
                           e.price_return_pct, e.market_move_pct, e.exit_reason
                    FROM core.executions e
                    JOIN core.orders o ON o.id = e.order_id
                    WHERE o.strategy_id = :strategy_id
                    ORDER BY e.executed_at DESC, e.id DESC
                    LIMIT :limit
                    """
                ),
                {"strategy_id": strategy_id, "limit": limit},
            )
            rows = list(reversed(result.mappings().all()))
        else:
            result = await self._session.execute(
                text(
                    """
                    SELECT e.id, e.order_id, e.portfolio_id, e.asset_id, e.side, e.quantity,
                           e.price, e.commission, e.net_amount, e.venue, e.executed_at,
                           e.created_at, e.realized_pnl,
                           e.price_return_pct, e.market_move_pct, e.exit_reason
                    FROM core.executions e
                    JOIN core.orders o ON o.id = e.order_id
                    WHERE o.strategy_id = :strategy_id
                    ORDER BY e.executed_at, e.id
                    """
                ),
                {"strategy_id": strategy_id},
            )
            rows = result.mappings().all()
        return [_row_to_execution(row) for row in rows]

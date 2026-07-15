# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
#   §API Standards: REST/FastAPI, versioned, Pydantic validation, OpenAPI.
# Doc 08 — Frontend Architecture (QH-008 v1.0) §API Layer: answers the
#   frontend execution service's existing call GET /v1/portfolios/{id}/orders
#   (features/execution/services).
# Doc 10 — API Specification (QH-010 v1.0): shared ResponseEnvelope.
# Doc 14 §10.7.3 Order Model / §10.7.4 Order Lifecycle (CREATED/VALIDATED/
#   REJECTED/FILLED, Step 3.5) / §10.9.4 Trade Recording: the order/execution
#   read shapes this exposes.
# Per Doc 00 §14.11
#
# Step 4.4, the Execution vertical slice: read endpoints over Phase 3.3/3.5's
# real core.orders / core.executions (written by the live
# Signal->Order->Risk->Fill loop). The order/execution blotter's data feed.
#
# JUDGMENT CALLS (Doc 00 §14.5/§14.7 — flagged):
#  1. snake_case JSON + Decimal-as-string, identical to Steps 4.2/4.3 (see
#     markets.py / portfolio.py). quantity/filled_quantity are NUMERIC(28,8)
#     and price/average_price NUMERIC(18,8), so ALL are STRINGS here, not
#     numbers — reconciling the Step 0.5 execution types (`quantity: number`).
#  2. ASSET ENRICHMENT: an order/execution row carries only asset_id; the
#     blotter is far more usable showing "BTC/USDT" than a UUID. Resolved by
#     reusing Step 4.1's AssetRepository.get_by_id, deduplicated per DISTINCT
#     asset_id (one lookup per distinct asset, not per row) — identical to
#     Step 4.3's PositionOut enrichment. Replace with a single orders⋈assets
#     JOIN read method only if an order list ever spans many distinct assets.
#  3. FILL PRICE ON THE ORDER: the blotter's "price" is the order's
#     average_price (VWAP fill price, §10.7.3), surfaced onto RecordedOrder in
#     this step (see domain/execution/entities.py). It is null for a
#     not-yet-filled (CREATED/VALIDATED) or REJECTED order — the blotter shows
#     "—" there. The full per-fill detail (multiple executions per order) is a
#     separate drill-down endpoint (GET /v1/orders/{id}/executions) over the
#     real ExecutionRepository, rather than inlining an execution list into
#     every blotter row (which the current single-full-fill model, F-16, would
#     make redundant anyway — one execution per order).
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Query, status
from pydantic import BaseModel, field_serializer

from quant_hub.api.dependencies import AssetRepo, ExecutionRepo, OrderRepo, PortfolioRepo, StrategyRepo
from quant_hub.api.envelope import ApiError, ErrorCode, ResponseEnvelope, ok
from quant_hub.domain.execution.entities import OrderSide, RecordedExecution, RecordedOrder
from quant_hub.domain.market_data.entities import Asset
from quant_hub.domain.strategy_engine.entities import RegisteredStrategy
from quant_hub.domain.strategy_engine.implied_sizing import DIRECTION_LONG, DIRECTION_SHORT

router = APIRouter(tags=["execution"])


class OrderOut(BaseModel):
    """API shape of a core.orders row (Doc 14 §10.7.3/§10.7.4), enriched with
    the asset's symbol/exchange plus strategy/direction context for display.
    Decimal fields render as strings.
    """

    id: UUID
    portfolio_id: UUID
    asset_id: UUID
    symbol: str | None
    exchange: str | None
    side: str
    # JUDGMENT CALL (Doc 00 §14.5/§14.7, flagged): `direction` is derived
    # straight from `side` (BUY -> LONG, SELL -> SHORT), NOT looked up via the
    # originating signal. S-5 scopes Order.side down to BUY/SELL only (no
    # Short/Cover distinction, domain/execution/entities.py::OrderSide) — for
    # this scoped-down model, order side already IS the same directional
    # concept implied_sizing.compute_direction expresses for a signal's
    # value sign. A signal lookup would be a redundant round-trip to
    # re-derive a fact the order already states.
    direction: str
    strategy_id: UUID | None
    strategy_name: str | None
    order_type: str
    quantity: Decimal
    filled_quantity: Decimal
    average_price: Decimal | None
    status: str
    signal_id: UUID | None
    realized_pnl: Decimal | None
    created_at: datetime

    @field_serializer("quantity", "filled_quantity", "average_price", "realized_pnl", when_used="json")
    def _serialize_decimal(self, value: Decimal | None) -> str | None:
        return None if value is None else format(value, "f")

    @classmethod
    def from_recorded(
        cls,
        order: RecordedOrder,
        asset: Asset | None,
        strategy: RegisteredStrategy | None,
        realized_pnl: Decimal | None,
    ) -> "OrderOut":
        return cls(
            id=order.id,
            portfolio_id=order.portfolio_id,
            asset_id=order.asset_id,
            symbol=asset.symbol if asset else None,
            exchange=asset.exchange if asset else None,
            side=order.side.value,
            direction=DIRECTION_LONG if order.side is OrderSide.BUY else DIRECTION_SHORT,
            strategy_id=order.strategy_id,
            strategy_name=strategy.name if strategy else None,
            order_type=order.order_type.value,
            quantity=order.quantity,
            filled_quantity=order.filled_quantity,
            average_price=order.average_price,
            status=order.status.value,
            signal_id=order.signal_id,
            realized_pnl=realized_pnl,
            created_at=order.created_at,
        )


class ExecutionOut(BaseModel):
    """API shape of a core.executions row — Doc 14 §10.9.4 Trade Recording.
    The immutable fill record for an order. Decimal fields render as strings.
    """

    id: UUID
    order_id: UUID
    portfolio_id: UUID
    asset_id: UUID
    side: str
    quantity: Decimal
    price: Decimal
    commission: Decimal
    net_amount: Decimal
    venue: str
    executed_at: datetime
    realized_pnl: Decimal | None

    @field_serializer("quantity", "price", "commission", "net_amount", "realized_pnl", when_used="json")
    def _serialize_decimal(self, value: Decimal | None) -> str | None:
        return None if value is None else format(value, "f")

    @classmethod
    def from_recorded(cls, execution: RecordedExecution) -> "ExecutionOut":
        return cls(
            id=execution.id,
            order_id=execution.order_id,
            portfolio_id=execution.portfolio_id,
            asset_id=execution.asset_id,
            side=execution.side.value,
            quantity=execution.quantity,
            price=execution.price,
            commission=execution.commission,
            net_amount=execution.net_amount,
            venue=execution.venue,
            executed_at=execution.executed_at,
            realized_pnl=execution.realized_pnl,
        )


@router.get(
    "/portfolios/{portfolio_id}/orders",
    response_model=ResponseEnvelope[list[OrderOut]],
    summary="Get orders for a portfolio (the blotter feed)",
)
async def get_portfolio_orders(
    portfolio_id: UUID,
    portfolio_repo: PortfolioRepo,
    order_repo: OrderRepo,
    asset_repo: AssetRepo,
    strategy_repo: StrategyRepo,
    execution_repo: ExecutionRepo,
    limit: int | None = Query(None, gt=0, le=5000),
) -> ResponseEnvelope[list[OrderOut]]:
    # 404 on an unknown portfolio so a client distinguishes "no such
    # portfolio" from "portfolio exists but has placed no orders" (empty list).
    if await portfolio_repo.get_by_id(portfolio_id) is None:
        raise ApiError(
            status.HTTP_404_NOT_FOUND,
            ErrorCode.RESOURCE_NOT_FOUND,
            f"Portfolio {portfolio_id} not found",
        )
    orders = await order_repo.list_by_portfolio(portfolio_id, limit=limit)
    # Resolve each DISTINCT asset/strategy once (judgment call #2 in module
    # docstring — same dedup-per-distinct-id pattern, now extended to
    # strategy_id).
    assets: dict[UUID, Asset | None] = {}
    strategies: dict[UUID, RegisteredStrategy | None] = {}
    for order in orders:
        if order.asset_id not in assets:
            assets[order.asset_id] = await asset_repo.get_by_id(order.asset_id)
        if order.strategy_id is not None and order.strategy_id not in strategies:
            strategies[order.strategy_id] = await strategy_repo.get_by_id(order.strategy_id)
    # F-16: the current simulated fill model is one execution per order, so a
    # single batch fetch + order_id map gives each order its fill's
    # realized_pnl without an N+1 get_by_order call per row.
    executions = await execution_repo.list_by_portfolio(portfolio_id)
    realized_by_order: dict[UUID, Decimal | None] = {e.order_id: e.realized_pnl for e in executions}
    return ok(
        [
            OrderOut.from_recorded(
                o,
                assets[o.asset_id],
                strategies.get(o.strategy_id) if o.strategy_id else None,
                realized_by_order.get(o.id),
            )
            for o in orders
        ]
    )


@router.get(
    "/orders/{order_id}/executions",
    response_model=ResponseEnvelope[list[ExecutionOut]],
    summary="Get execution fills for an order",
)
async def get_order_executions(
    order_id: UUID,
    order_repo: OrderRepo,
    execution_repo: ExecutionRepo,
) -> ResponseEnvelope[list[ExecutionOut]]:
    # 404 on an unknown order so a client distinguishes "no such order" from
    # "order exists but has no fills yet" (CREATED/REJECTED -> empty list).
    if await order_repo.get_by_id(order_id) is None:
        raise ApiError(
            status.HTTP_404_NOT_FOUND,
            ErrorCode.RESOURCE_NOT_FOUND,
            f"Order {order_id} not found",
        )
    executions = await execution_repo.get_by_order(order_id)
    return ok([ExecutionOut.from_recorded(e) for e in executions])


@router.get(
    "/portfolios/{portfolio_id}/executions",
    response_model=ResponseEnvelope[list[ExecutionOut]],
    summary="Get all execution fills for a portfolio (batch feed for analytics)",
)
async def get_portfolio_executions(
    portfolio_id: UUID,
    portfolio_repo: PortfolioRepo,
    execution_repo: ExecutionRepo,
) -> ResponseEnvelope[list[ExecutionOut]]:
    # 404 on an unknown portfolio, matching get_portfolio_orders' convention.
    if await portfolio_repo.get_by_id(portfolio_id) is None:
        raise ApiError(
            status.HTTP_404_NOT_FOUND,
            ErrorCode.RESOURCE_NOT_FOUND,
            f"Portfolio {portfolio_id} not found",
        )
    executions = await execution_repo.list_by_portfolio(portfolio_id)
    return ok([ExecutionOut.from_recorded(e) for e in executions])


@router.get(
    "/strategies/{strategy_id}/orders",
    response_model=ResponseEnvelope[list[OrderOut]],
    summary="Get orders generated by a strategy (the strategy-scoped blotter feed)",
)
async def get_strategy_orders(
    strategy_id: UUID,
    strategy_repo: StrategyRepo,
    order_repo: OrderRepo,
    asset_repo: AssetRepo,
    execution_repo: ExecutionRepo,
    limit: int | None = Query(None, gt=0, le=5000),
) -> ResponseEnvelope[list[OrderOut]]:
    # Filters on core.orders.strategy_id directly (real FK lineage) rather
    # than routing through the strategy's own portfolio_id, which is unset
    # for every currently-registered strategy — see list_by_strategy docstring.
    strategy = await strategy_repo.get_by_id(strategy_id)
    if strategy is None:
        raise ApiError(
            status.HTTP_404_NOT_FOUND,
            ErrorCode.RESOURCE_NOT_FOUND,
            f"Strategy {strategy_id} not found",
        )
    orders = await order_repo.list_by_strategy(strategy_id, limit=limit)
    assets: dict[UUID, Asset | None] = {}
    for order in orders:
        if order.asset_id not in assets:
            assets[order.asset_id] = await asset_repo.get_by_id(order.asset_id)
    executions = await execution_repo.list_by_strategy(strategy_id, limit=limit)
    realized_by_order: dict[UUID, Decimal | None] = {e.order_id: e.realized_pnl for e in executions}
    return ok(
        [
            OrderOut.from_recorded(o, assets[o.asset_id], strategy, realized_by_order.get(o.id))
            for o in orders
        ]
    )


@router.get(
    "/strategies/{strategy_id}/executions",
    response_model=ResponseEnvelope[list[ExecutionOut]],
    summary="Get all execution fills generated by a strategy (batch feed for analytics)",
)
async def get_strategy_executions(
    strategy_id: UUID,
    strategy_repo: StrategyRepo,
    execution_repo: ExecutionRepo,
    limit: int | None = Query(None, gt=0, le=5000),
) -> ResponseEnvelope[list[ExecutionOut]]:
    if await strategy_repo.get_by_id(strategy_id) is None:
        raise ApiError(
            status.HTTP_404_NOT_FOUND,
            ErrorCode.RESOURCE_NOT_FOUND,
            f"Strategy {strategy_id} not found",
        )
    executions = await execution_repo.list_by_strategy(strategy_id, limit=limit)
    return ok([ExecutionOut.from_recorded(e) for e in executions])

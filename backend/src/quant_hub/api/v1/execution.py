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

from fastapi import APIRouter, status
from pydantic import BaseModel, field_serializer

from quant_hub.api.dependencies import AssetRepo, ExecutionRepo, OrderRepo, PortfolioRepo
from quant_hub.api.envelope import ApiError, ErrorCode, ResponseEnvelope, ok
from quant_hub.domain.execution.entities import RecordedExecution, RecordedOrder
from quant_hub.domain.market_data.entities import Asset

router = APIRouter(tags=["execution"])


class OrderOut(BaseModel):
    """API shape of a core.orders row (Doc 14 §10.7.3/§10.7.4), enriched with
    the asset's symbol/exchange for display. Decimal fields render as strings.
    """

    id: UUID
    portfolio_id: UUID
    asset_id: UUID
    symbol: str | None
    exchange: str | None
    side: str
    order_type: str
    quantity: Decimal
    filled_quantity: Decimal
    average_price: Decimal | None
    status: str
    signal_id: UUID | None
    created_at: datetime

    @field_serializer("quantity", "filled_quantity", "average_price", when_used="json")
    def _serialize_decimal(self, value: Decimal | None) -> str | None:
        return None if value is None else format(value, "f")

    @classmethod
    def from_recorded(cls, order: RecordedOrder, asset: Asset | None) -> "OrderOut":
        return cls(
            id=order.id,
            portfolio_id=order.portfolio_id,
            asset_id=order.asset_id,
            symbol=asset.symbol if asset else None,
            exchange=asset.exchange if asset else None,
            side=order.side.value,
            order_type=order.order_type.value,
            quantity=order.quantity,
            filled_quantity=order.filled_quantity,
            average_price=order.average_price,
            status=order.status.value,
            signal_id=order.signal_id,
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

    @field_serializer("quantity", "price", "commission", "net_amount", when_used="json")
    def _serialize_decimal(self, value: Decimal) -> str:
        return format(value, "f")

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
) -> ResponseEnvelope[list[OrderOut]]:
    # 404 on an unknown portfolio so a client distinguishes "no such
    # portfolio" from "portfolio exists but has placed no orders" (empty list).
    if await portfolio_repo.get_by_id(portfolio_id) is None:
        raise ApiError(
            status.HTTP_404_NOT_FOUND,
            ErrorCode.RESOURCE_NOT_FOUND,
            f"Portfolio {portfolio_id} not found",
        )
    orders = await order_repo.list_by_portfolio(portfolio_id)
    # Resolve each DISTINCT asset once (judgment call #2 in module docstring).
    assets: dict[UUID, Asset | None] = {}
    for order in orders:
        if order.asset_id not in assets:
            assets[order.asset_id] = await asset_repo.get_by_id(order.asset_id)
    return ok([OrderOut.from_recorded(o, assets[o.asset_id]) for o in orders])


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

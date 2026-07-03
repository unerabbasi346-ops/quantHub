# Governing specification: Doc 14 §10.7.4 (Order Lifecycle), §10.8.6 (Fill
#   Handling), §10.9.3 (Trade Lifecycle), §10.6.6 (Position Management)
# Doc 02: Risk Engine must approve every order before routing — mandatory gate
# Layer: Application — Doc 07 §Layers
# Service: Execution — Doc 07 §Core Services
# Invariants: P-2 (immutability), P-5 (audit trail), P-13 (determinism of the
#   position math), Port-3
# Scope: handbook/KNOWN_LIMITATIONS.md S-5 / F-16, F-17
# Per Doc 00 §14.11
from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal

from quant_hub.domain.execution.entities import (
    OrderStatus,
    RecordedExecution,
    RecordedOrder,
)
from quant_hub.domain.execution.interfaces import (
    ExecutionRepository,
    OrderRepository,
    RiskApprovalInterface,
)
from quant_hub.domain.execution.simulation import simulate_fill
from quant_hub.domain.portfolio.interfaces import PositionRepository
from quant_hub.domain.portfolio.positions import RecordedPosition, apply_fill_to_position
from quant_hub.domain.risk.entities import PreTradeRiskRequest

logger = logging.getLogger(__name__)

_MV_SCALE = Decimal("0.0001")  # core.positions.market_value NUMERIC(20,4)
_ZERO = Decimal("0")


@dataclass(frozen=True)
class ExecutionOutcome:
    """Result of running one CREATED order through the trade loop — the
    §10.9.3 trade-lifecycle outcome for one order.

    `terminal_status` is FILLED for an approved+filled order or REJECTED for a
    risk-rejected one. `execution` / `position` are populated only on the
    filled path.
    """

    order_id: object
    terminal_status: OrderStatus
    approved: bool
    rejection_reason: str | None
    execution: RecordedExecution | None
    position: RecordedPosition | None


class ExecutionService:
    """Closes the trade loop — Doc 14 §10.7.4/§10.8/§10.9.

    Takes a CREATED order (Step 3.3 output) plus its pre-trade risk request
    (Step 3.4 context) and drives it to a terminal state:

      approved  -> VALIDATED -> simulated fill (§10.8.6) -> core.executions
                -> FILLED -> position update (§10.6.6)
      rejected  -> REJECTED (reason recorded in analytics.risk_assessments,
                   Step 3.4; logged here — §10.7.5 no silent rejection)

    Doc 02: risk_gate is a mandatory dependency; every order is evaluated
    before it can fill. Does not commit — the caller owns the transaction
    boundary (Doc 07 §Implementation Rules), so the whole order->fill->position
    sequence is one atomic unit.
    """

    def __init__(
        self,
        orders: OrderRepository,
        executions: ExecutionRepository,
        positions: PositionRepository,
        risk_gate: RiskApprovalInterface,  # Doc 02: mandatory pre-trade gate
    ) -> None:
        self._orders = orders
        self._executions = executions
        self._positions = positions
        self._risk_gate = risk_gate

    async def process_order(
        self,
        order: RecordedOrder,
        risk_request: PreTradeRiskRequest,
        executed_at: object,
    ) -> ExecutionOutcome:
        """Run one order through gate -> (validate|reject) -> fill -> position.

        The simulated fill executes at `risk_request.price` — the current
        market price the order was risk-assessed against (immediate simulated
        fill; no routing round-trip, F-16).
        """
        decision = await self._risk_gate.evaluate(risk_request)

        if not decision.approved:
            # §10.7.5: rejection reason recorded (analytics.risk_assessments,
            # Step 3.4) and surfaced here — never silently swallowed.
            await self._orders.mark_rejected(order.id)
            logger.warning(
                "order REJECTED by pre-trade risk: order_id=%s reason=%s",
                order.id, decision.reason,
            )
            return ExecutionOutcome(
                order_id=order.id,
                terminal_status=OrderStatus.REJECTED,
                approved=False,
                rejection_reason=decision.reason,
                execution=None,
                position=None,
            )

        # Approved: CREATED -> VALIDATED (§10.7.4).
        validated = await self._orders.mark_validated(order.id)

        # Simulated fill (§10.8.6). Fill-validation guard: fill quantity must
        # not exceed the order's remaining quantity. A fresh order has filled
        # 0, so remaining == quantity; the full fill satisfies this exactly.
        fill = simulate_fill(validated, risk_request.price, executed_at)
        if fill.quantity > validated.quantity:  # defensive; simulate_fill never overshoots
            raise ValueError("simulated fill exceeds order quantity")

        execution = await self._executions.record(fill)
        await self._orders.mark_filled(order.id, fill.quantity, fill.price)

        # Position update (§10.6.6 / §10.9.3): recompute quantity + average
        # price from the fill; mark-to-market value at the fill price.
        current = await self._positions.get_by_portfolio_and_asset(
            order.portfolio_id, order.asset_id
        )
        cur_qty = current.quantity if current is not None else _ZERO
        cur_avg = current.average_entry_price if current is not None else _ZERO
        update = apply_fill_to_position(cur_qty, cur_avg, fill.signed_quantity, fill.price)
        market_value = (update.quantity * fill.price).quantize(_MV_SCALE, rounding=ROUND_HALF_EVEN)

        # Step 3.6 (§10.9.5): persist mark-to-market unrealized P&L and
        # accumulate realized P&L from this fill (0 for pure opens/adds).
        position = await self._positions.upsert(
            order.portfolio_id,
            order.asset_id,
            quantity=update.quantity,
            average_entry_price=update.average_entry_price,
            market_value=market_value,
            unrealized_pnl=update.unrealized_pnl,
            realized_pnl_delta=update.realized_pnl,
            last_price=fill.price,
            last_price_at=executed_at,
            is_closed=update.is_closed,
        )
        return ExecutionOutcome(
            order_id=order.id,
            terminal_status=OrderStatus.FILLED,
            approved=True,
            rejection_reason=None,
            execution=execution,
            position=position,
        )

# Governing specification: Doc 14 §10.6.5 — Order Generation ("Order Quantity")
# Layer: Domain — Doc 07 §Layers (pure deterministic computation; no I/O)
# Invariants: P-1 (no strategy-specific logic — §10.7.5), P-13 (determinism)
# Scope: handbook/KNOWN_LIMITATIONS.md S-5
# Per Doc 00 §14.11
#
# The heart of Order Generation: convert an ABSOLUTE §11.2 target into a
# tradeable order by differencing against the current position (§10.6.5 "Order
# Quantity computed considering current positions"). Pure and deterministic
# (P-13): identical inputs -> identical OrderIntent, so it is exhaustively
# unit-testable with no DB. The non-deterministic part (the UUID v7 idempotency
# key, §10.7.5) is deliberately NOT generated here — it is a parameter, so this
# function stays a pure function of its inputs.
from __future__ import annotations

from decimal import ROUND_DOWN, Decimal
from uuid import UUID

from quant_hub.domain.execution.entities import (
    CurrentPosition,
    OrderIntent,
    OrderSide,
    OrderType,
    TargetPosition,
    TimeInForce,
)

# Quantity column scale — NUMERIC(28,8) after Step 3.0 (F-1..F-4 resolution).
_QUANTITY_SCALE = Decimal("0.00000001")


def compute_order_intent(
    *,
    target: TargetPosition,
    current: CurrentPosition,
    portfolio_id: UUID,
    strategy_id: UUID | None,
    signal_id: UUID | None,
    idempotency_key: UUID,
    min_quantity: Decimal = Decimal("0"),
) -> OrderIntent | None:
    """Compute the order that moves `current` toward `target`, or None if none
    is needed.

    §10.6.5 "Order Quantity — Order quantity computed considering current
    positions, position limits, and capital allocation":

        target_quantity = (target_weight x portfolio_value) / reference_price
        delta           = target_quantity - current_quantity
        side            = BUY if delta > 0 else SELL
        quantity        = |delta|

    Returns None ("no order") when |delta| <= min_quantity — i.e. the portfolio
    is already at (or within min_quantity of) the target, so trading would only
    add cost. With the default min_quantity=0 only an EXACT-target position is a
    no-op; a flat position against a non-zero target always yields an order.

    QUANTIZATION (judgment call, flagged — Doc 00 §14.5/§14.7): target_quantity
    is a Decimal division that can be non-terminating, so it is quantized to the
    quantity column's scale (8 dp) with ROUND_DOWN. ROUND_DOWN (toward zero) is
    chosen so a rounded order never overshoots the intended exposure — the
    conservative direction for a risk-managed platform (Port-2). This is NOT
    exchange lot-size / min-notional stepping (§10.7.5 "Quantity Validation —
    within minimum and maximum limits"): real per-instrument lot/tick rounding
    needs exchange metadata not modeled in Phase 3A and is deferred to Step 3.4
    Pre-Trade Risk. `min_quantity` is caller-supplied, not a hardcoded lot size.

    POSITION/CAPITAL LIMITS (scoped out, flagged): §10.6.5 also says quantity is
    computed "considering position limits and capital allocation". Those
    pre-trade limit checks are §10.7.5 validation — Step 3.4 — not applied here.
    Sizing's §11.3.4 max-position cap (Step 3.1) already bounded the notional
    upstream; a second order-level limit gate is Step 3.4's job.

    NO CROSS-ZERO SPLIT (flagged): if `current` is long and `target` is short
    (or vice versa), a single BUY/SELL for the net delta is produced. Splitting
    into a close-then-open pair (and the SHORT/COVER side distinction) is
    deferred with OrderSide's SHORT/COVER (see entities.py).
    """
    if target.reference_price <= 0:
        raise ValueError(f"reference_price must be positive, got {target.reference_price}")
    if min_quantity < 0:
        raise ValueError(f"min_quantity must be non-negative, got {min_quantity}")

    target_quantity = target.target_quantity.quantize(_QUANTITY_SCALE, rounding=ROUND_DOWN)
    delta = target_quantity - current.quantity

    if abs(delta) <= min_quantity:
        return None

    side = OrderSide.BUY if delta > 0 else OrderSide.SELL
    quantity = abs(delta)

    return OrderIntent(
        idempotency_key=idempotency_key,
        portfolio_id=portfolio_id,
        strategy_id=strategy_id,
        asset=target.asset,
        side=side,
        quantity=quantity,
        order_type=OrderType.MARKET,
        time_in_force=TimeInForce.DAY,
        reference_price=target.reference_price,
        target_quantity=target_quantity,
        current_quantity=current.quantity,
        delta_quantity=delta,
        signal_id=signal_id,
    )

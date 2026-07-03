# Governing specification: Doc 14 §10.8.6 — Fill Handling
#                          Doc 14 §10.5 — Paper Trading (Simulated Fill Engine)
# Layer: Domain — Doc 07 §Layers (pure computation; no persistence, no I/O)
# Invariants: P-13 (determinism), P-2 (immutability)
# Scope: handbook/KNOWN_LIMITATIONS.md S-5 / F-16 (simulated-fill realism)
# Per Doc 00 §14.11
#
# Step 3.5: the simulated fill engine. Given a VALIDATED order and a market
# price, it produces a full fill at that price. Deterministic per P-13 —
# identical (order, price) always yield an identical fill.
#
# SCOPED DOWN (S-5, F-16): §10.5's paper-trading engine specifies slippage
# models (fixed/proportional/market-impact) and partial fills where size
# exceeds displayed liquidity. NONE of that is modeled here — this is a full
# fill of the whole order quantity at the supplied price, zero commission,
# venue "SIM". The realism knobs are deferred with the rest of the
# paper/live-trading operational infrastructure S-5 excludes.
from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal

from quant_hub.domain.execution.entities import Fill, RecordedOrder

# core.executions.price is NUMERIC(18,8); quantize the fill price to that
# scale so the domain value matches what is persisted (no silent rounding at
# the DB boundary). Banker's rounding — a price is not an exposure figure
# (unlike order quantity, which ROUND_DOWNs to never overshoot, §10.6.5), so
# nearest-even is the neutral choice for a mid-market simulated fill.
_PRICE_SCALE = Decimal("0.00000001")


def simulate_fill(
    order: RecordedOrder,
    market_price: Decimal,
    executed_at: object,
    *,
    venue: str = "SIM",
) -> Fill:
    """Produce a simulated full fill for a VALIDATED order — §10.8.6 / §10.5.

    Full fill: the entire order quantity fills at `market_price`, zero
    commission (F-16). The order's quantity is already the absolute,
    8-dp-quantized size from Order Generation (§10.6.5, Step 3.3), so it is
    carried through unchanged — the fill never exceeds the order (satisfying
    §10.8.6 "fill quantity does not exceed remaining order quantity" trivially).
    """
    price = market_price.quantize(_PRICE_SCALE, rounding=ROUND_HALF_EVEN)
    return Fill(
        order_id=order.id,
        portfolio_id=order.portfolio_id,
        asset_id=order.asset_id,
        side=order.side,
        quantity=order.quantity,
        price=price,
        commission=Decimal("0"),
        venue=venue,
        executed_at=executed_at,
    )

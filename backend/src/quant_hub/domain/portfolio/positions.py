# Governing specification: Doc 14 §10.6.6 — Position Management
#                          Doc 14 §10.9.3 — Trade Lifecycle (Position Updated)
# Layer: Domain — Doc 07 §Layers (value objects + pure computation; no I/O)
# Invariants: P-2 (immutability), P-13 (determinism)
# Scope: handbook/KNOWN_LIMITATIONS.md S-5 / F-17
# Per Doc 00 §14.11
#
# Position state, the pure fill-application rule, and (Step 3.6) the P&L it
# produces. §10.6.6 lists a position's state as quantity, average price, and
# unrealized P&L; §10.9.3/§10.9.5 require "Position quantity, average price,
# unrealized P&L recalculated" and realized P&L "on trade execution" for
# closing trades. This module owns the deterministic quantity + average-price
# recomputation AND (Step 3.6, resolving F-17) the realized/unrealized P&L for
# the fill.
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal
from uuid import UUID

_QTY_SCALE = Decimal("0.00000001")    # core.positions.quantity NUMERIC(28,8)
_PRICE_SCALE = Decimal("0.00000001")  # core.positions.average_entry_price NUMERIC(18,8)
_PNL_SCALE = Decimal("0.0001")        # core.positions P&L columns NUMERIC(20,4)
_ZERO = Decimal("0")


@dataclass(frozen=True)
class RecordedPosition:
    """A persisted position — the core.positions view (§10.6.6).

    Signed `quantity` (long > 0, short < 0, 0 = flat, NUMERIC(28,8) after
    Step 3.0). `average_entry_price` is the cost basis for the open position.
    `market_value` / `last_price` / `unrealized_pnl` / `realized_pnl_today` are
    the mark-to-market view maintained on every fill (Step 3.6, §10.9.5).
    Immutable snapshot per P-2; the repository writes the next snapshot.
    """

    id: UUID
    portfolio_id: UUID
    asset_id: UUID
    quantity: Decimal
    average_entry_price: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    realized_pnl_today: Decimal
    last_price: Decimal | None
    is_closed: bool
    sequence_number: int


@dataclass(frozen=True)
class PositionUpdate:
    """The next position state computed from a fill — pure result, no I/O.

    §10.6.6 quantity + average price, plus (Step 3.6) the P&L this fill
    produces: `realized_pnl` for the portion of an opposing position it closes
    (§10.9.5), and `unrealized_pnl` for the resulting open position marked at
    the fill price. `realized_pnl` is the increment from THIS fill (0 for pure
    opens/adds), to be accumulated into realized_pnl_today by the caller.
    """

    quantity: Decimal
    average_entry_price: Decimal
    is_closed: bool
    realized_pnl: Decimal
    unrealized_pnl: Decimal


def apply_fill_to_position(
    current_quantity: Decimal,
    current_average_price: Decimal,
    fill_signed_quantity: Decimal,
    fill_price: Decimal,
) -> PositionUpdate:
    """Recompute (quantity, average price, P&L) after a fill — §10.6.6/§10.9.5.

    Deterministic per P-13. Standard signed-position average-cost accounting:

    - Opening from flat        -> average = fill price; realized 0.
    - Adding in same direction -> size-weighted average of old and fill;
                                  realized 0.
    - Reducing (partial close) -> average UNCHANGED; realized on the closed
                                  quantity.
    - Fully closing (-> 0)      -> average resets to 0; realized on the whole
                                  position.
    - Crossing zero (sign flip) -> existing position fully closed (realized on
                                  it), new position opened at the fill price.

    Realized P&L for a closed quantity q (§10.9.5, "(exit − entry) × quantity"):
    long closed by a SELL  -> (fill_price − entry_avg) × q
    short closed by a BUY   -> (entry_avg − fill_price) × q
    Unrealized P&L of the resulting position marked at the fill price:
    (fill_price − new_average) × new_quantity (signed).
    """
    new_quantity = (current_quantity + fill_signed_quantity).quantize(
        _QTY_SCALE, rounding=ROUND_HALF_EVEN
    )
    realized = _ZERO

    if current_quantity == _ZERO:
        new_average = fill_price                             # opening
    elif (current_quantity > _ZERO) == (fill_signed_quantity > _ZERO):
        # same direction — size-weighted average by absolute quantities
        gross = abs(current_quantity) * current_average_price + abs(fill_signed_quantity) * fill_price
        new_average = gross / abs(new_quantity)
    else:
        # opposite direction — reduce / close / cross: realize P&L on the
        # quantity of the existing position that is closed out.
        closed_qty = min(abs(fill_signed_quantity), abs(current_quantity))
        if current_quantity > _ZERO:                         # closing a long via SELL
            realized = (fill_price - current_average_price) * closed_qty
        else:                                                # closing a short via BUY
            realized = (current_average_price - fill_price) * closed_qty

        if abs(fill_signed_quantity) < abs(current_quantity):
            new_average = current_average_price              # partial close
        elif abs(fill_signed_quantity) == abs(current_quantity):
            new_average = _ZERO                              # fully flat
        else:
            new_average = fill_price                         # crossed zero

    new_average = new_average.quantize(_PRICE_SCALE, rounding=ROUND_HALF_EVEN)
    unrealized = ((fill_price - new_average) * new_quantity).quantize(
        _PNL_SCALE, rounding=ROUND_HALF_EVEN
    )
    return PositionUpdate(
        quantity=new_quantity,
        average_entry_price=new_average,
        is_closed=(new_quantity == _ZERO),
        realized_pnl=realized.quantize(_PNL_SCALE, rounding=ROUND_HALF_EVEN),
        unrealized_pnl=unrealized,
    )

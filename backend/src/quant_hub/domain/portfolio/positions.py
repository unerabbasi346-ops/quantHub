# Governing specification: Doc 14 §10.6.6 — Position Management
#                          Doc 14 §10.9.3 — Trade Lifecycle (Position Updated)
# Layer: Domain — Doc 07 §Layers (value objects + pure computation; no I/O)
# Invariants: P-2 (immutability), P-13 (determinism)
# Scope: handbook/KNOWN_LIMITATIONS.md S-5 / F-17
# Per Doc 00 §14.11
#
# Step 3.5: position state and the pure fill-application rule. §10.6.6 lists a
# position's state as quantity, average price, and unrealized P&L; §10.9.3
# requires "Position quantity, average price, unrealized P&L recalculated" on
# every fill. This module owns the deterministic quantity + average-price
# recomputation. UNREALIZED / REALIZED P&L are deferred to Step 3.6 (the P&L
# engine, §10.9.5) per S-5 (F-17) — this step establishes the position state
# they will be computed against.
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal
from uuid import UUID

_QTY_SCALE = Decimal("0.00000001")    # core.positions.quantity NUMERIC(28,8)
_PRICE_SCALE = Decimal("0.00000001")  # core.positions.average_entry_price NUMERIC(18,8)
_ZERO = Decimal("0")


@dataclass(frozen=True)
class RecordedPosition:
    """A persisted position — the core.positions view (§10.6.6).

    Signed `quantity` (long > 0, short < 0, 0 = flat, NUMERIC(28,8) after
    Step 3.0). `average_entry_price` is the cost basis for the open position.
    Immutable snapshot per P-2; the repository writes the next snapshot.
    """

    id: UUID
    portfolio_id: UUID
    asset_id: UUID
    quantity: Decimal
    average_entry_price: Decimal
    is_closed: bool
    sequence_number: int


@dataclass(frozen=True)
class PositionUpdate:
    """The next position state computed from a fill — pure result, no I/O.

    Carries only the fields Step 3.5 recomputes (§10.6.6 quantity + average
    price). market_value / P&L are the persistence/§3.6 layer's concern.
    """

    quantity: Decimal
    average_entry_price: Decimal
    is_closed: bool


def apply_fill_to_position(
    current_quantity: Decimal,
    current_average_price: Decimal,
    fill_signed_quantity: Decimal,
    fill_price: Decimal,
) -> PositionUpdate:
    """Recompute (quantity, average price) after a fill — §10.6.6 / §10.9.3.

    Deterministic per P-13. Standard signed-position accounting:

    - Opening from flat        -> average = fill price.
    - Adding in same direction -> size-weighted average of old and fill.
    - Reducing (partial close) -> average UNCHANGED (only quantity shrinks).
    - Fully closing (-> 0)      -> average resets to 0, position flat.
    - Crossing zero (sign flip) -> new position opened at the fill price.

    REALIZED P&L on the reducing/closing/crossing branches is NOT computed
    here — that is the Step 3.6 P&L engine's job (§10.9.5, F-17). This
    function only maintains position state (quantity + cost basis).
    """
    new_quantity = (current_quantity + fill_signed_quantity).quantize(
        _QTY_SCALE, rounding=ROUND_HALF_EVEN
    )

    if current_quantity == _ZERO:
        new_average = fill_price
    elif (current_quantity > _ZERO) == (fill_signed_quantity > _ZERO):
        # same direction — size-weighted average by absolute quantities
        gross = abs(current_quantity) * current_average_price + abs(fill_signed_quantity) * fill_price
        new_average = gross / abs(new_quantity)
    else:
        # opposite direction — reduce / close / cross
        if abs(fill_signed_quantity) < abs(current_quantity):
            new_average = current_average_price          # partial close
        elif abs(fill_signed_quantity) == abs(current_quantity):
            new_average = _ZERO                          # fully flat
        else:
            new_average = fill_price                     # crossed zero

    new_average = new_average.quantize(_PRICE_SCALE, rounding=ROUND_HALF_EVEN)
    return PositionUpdate(
        quantity=new_quantity,
        average_entry_price=new_average,
        is_closed=(new_quantity == _ZERO),
    )

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
_MARGIN_SCALE = Decimal("0.00000001")  # core.positions.margin_used NUMERIC(28,8)
_LIQ_SCALE = Decimal("0.00000001")     # core.positions.liquidation_price NUMERIC(18,8)
_ZERO = Decimal("0")
_ONE = Decimal("1")

# Maintenance-margin rate default for the liquidation-price computation.
# JUDGMENT CALL (Doc 00 §14.5/§14.7 — flagged, S-10): a FLAT rate, not the
# tiered/notional-banded maintenance-margin schedule real venues (Binance et
# al.) apply — 0.5% is a representative low-tier BTC-perp figure. A real
# per-instrument tiered schedule is deferred (needs a venue margin-tier table
# this platform does not ingest); the computation below takes mmr as a
# parameter so a tiered lookup can replace this default without changing it.
_DEFAULT_MAINTENANCE_MARGIN_RATE = Decimal("0.005")


@dataclass(frozen=True)
class RecordedPosition:
    """A persisted position — the core.positions view (§10.6.6).

    Signed `quantity` (long > 0, short < 0, 0 = flat, NUMERIC(28,8) after
    Step 3.0). `average_entry_price` is the cost basis for the open position.
    `market_value` / `last_price` / `unrealized_pnl` / `realized_pnl_today` are
    the mark-to-market view maintained on every fill (Step 3.6, §10.9.5).
    Immutable snapshot per P-2; the repository writes the next snapshot.

    MARGIN STATE (migration e7a3c1f5b9d2, §10.6.6 "Margin Monitoring") — all
    None for a spot/unleveraged position (honest absence, not a fabricated
    leverage=1); populated only for a perpetual position. `leverage` is the
    configured multiplier, `margin_used` the collateral committed, and
    `liquidation_price` the mark at which the position is force-closed. These
    are STORAGE only here; the fill→position path that computes them is Step 3,
    and the authoritative collateral/equity figure behind them stays F-19's
    open gap. Additive with defaults so the Step 3.6 fill path keeps
    constructing RecordedPosition unchanged until Step 3 wires them.
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
    leverage: Decimal | None = None
    margin_used: Decimal | None = None
    liquidation_price: Decimal | None = None


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


@dataclass(frozen=True)
class MarginState:
    """The margin footprint of a leveraged (perpetual) position — the storage
    for core.positions.{margin_used, liquidation_price} (migration
    e7a3c1f5b9d2). `margin_used` is the isolated collateral committed;
    `liquidation_price` is the mark at which the position is force-closed
    (None for a flat position, which has no liquidation). Pure result, no I/O.
    """

    margin_used: Decimal
    liquidation_price: Decimal | None


def compute_perpetual_margin(
    signed_quantity: Decimal,
    average_entry_price: Decimal,
    leverage: Decimal,
    maintenance_margin_rate: Decimal = _DEFAULT_MAINTENANCE_MARGIN_RATE,
) -> MarginState:
    """Isolated-margin footprint of a one-way linear-perpetual position — pure,
    deterministic (P-13). Doc 14 §10.6.6 "Margin Monitoring"; S-10.

    Model (JUDGMENT CALLS, §14.5/§14.7 — flagged, all recorded in S-10):
      - ISOLATED margin, ONE-WAY (net) mode (the position-mode decision) — margin
        is per-position collateral, not a shared cross-margin pool.
      - LINEAR (USDT-margined) perpetual: notional = |qty| x price in quote
        currency. Inverse (coin-margined) contracts are out of scope (S-10).
      - `margin_used` = initial margin = notional_at_entry / leverage.
      - `liquidation_price` uses the standard entry-notional approximation:
            long : entry x (1 - 1/L + mmr)
            short: entry x (1 + 1/L - mmr)
        It IGNORES accrued funding and trading fees (both move the real liq
        price); funding is tracked separately as a §10.9.5 financing cashflow
        (Step 4), not folded into the liq price here. Flagged, not silently
        assumed exact.
      - F-19 INTERACTION: this is the position's own margin math; it does NOT
        consult a portfolio equity/collateral ledger (none exists — F-19). It
        answers "what collateral does THIS position tie up / where does it
        liquidate", not "does the account have that collateral".

    A flat position (signed_quantity == 0) has zero margin and no liquidation
    price. leverage must be > 0.
    """
    if leverage <= _ZERO:
        raise ValueError("leverage must be > 0")
    if signed_quantity == _ZERO:
        return MarginState(margin_used=_ZERO, liquidation_price=None)

    abs_qty = abs(signed_quantity)
    notional = abs_qty * average_entry_price
    margin_used = (notional / leverage).quantize(_MARGIN_SCALE, rounding=ROUND_HALF_EVEN)

    inv_leverage = _ONE / leverage
    if signed_quantity > _ZERO:  # long
        liq = average_entry_price * (_ONE - inv_leverage + maintenance_margin_rate)
    else:                        # short
        liq = average_entry_price * (_ONE + inv_leverage - maintenance_margin_rate)
    # A liquidation price can never be negative; a deep-enough (1/L > 1) short
    # cannot be liquidated to the downside in this model, so floor at 0.
    liq = max(liq, _ZERO).quantize(_LIQ_SCALE, rounding=ROUND_HALF_EVEN)
    return MarginState(margin_used=margin_used, liquidation_price=liq)

# Governing specification: Doc 14 §10.7.3 — Order Model; §10.7.4 — Order Lifecycle
# Layer: Domain — Doc 07 §Layers (value objects; no persistence, no I/O)
# Invariants: P-1 (methodology/strategy logic external), P-2 (immutability), P-13 (determinism)
# Scope: handbook/KNOWN_LIMITATIONS.md S-5 (Phase 3A scoped-down)
# Per Doc 00 §14.11
#
# Step 3.3: the canonical Order Model (§10.7.3) and its inputs, as immutable
# value objects. Order Generation (§10.6.5) is a pure PLATFORM mechanism — it
# has no external methodology plugin the way Sizing (§11.3) and Construction
# (§11.2) do, because §10.7.5 requires "Validation shall not embed
# strategy-specific logic per P-1" and quantity computation (§10.6.5 "Order
# Quantity") is deterministic platform arithmetic, not a strategy choice.
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from uuid import UUID

from quant_hub.domain.market_data.entities import AssetRef


class OrderSide(str, Enum):
    """Order side — Doc 14 §10.7.3 "Side".

    SCOPED DOWN (S-5, flagged): §10.7.3 lists "Buy, Sell, Short, Cover". Only
    BUY/SELL are modeled here. SHORT/COVER encode a position-intent
    distinction (opening vs. closing a short) that requires position-aware
    classification beyond a signed delta and has no meaning for the spot
    crypto instruments this Phase 3A slice exercises. Deferred until a
    shortable/derivative venue and its position semantics exist.
    """

    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    """Order type — Doc 14 §10.7.3 "Order Type".

    SCOPED DOWN (S-5, flagged): §10.7.3 lists "Market, Limit, Stop,
    Stop-Limit, Trailing Stop, OCO, or other". Only MARKET is modeled. Limit/
    stop/OCO orders carry price/trigger machinery and an order-slicing/parent
    relationship (§10.7.3 "Parent Order Reference", §10.7.6 "Order Slicing")
    that is deferred per S-5. A market order needs no limit_price/stop_price,
    so those columns (Step 1.1 schema) are left NULL this step.
    """

    MARKET = "MARKET"


class TimeInForce(str, Enum):
    """Time-in-force — Doc 14 §10.7.3 "Time-in-Force".

    SCOPED DOWN (S-5): §10.7.3 lists "Day, GTC, IOC, FOK, GTD". Only DAY (the
    Step 1.1 schema default) is used. The others govern resting-order
    lifetime, irrelevant to the simulated immediate-fill execution of Step 3.5.
    """

    DAY = "DAY"


class OrderStatus(str, Enum):
    """Order lifecycle state — Doc 14 §10.7.4.

    Step 3.3 writes CREATED — "Order has been created from a validated
    signal. Not yet validated for routing." (§10.7.4). Step 3.4 (Pre-Trade
    Risk, §10.7.5) drives CREATED -> VALIDATED / REJECTED. Step 3.5
    (Execution, §10.8/§10.9) drives VALIDATED -> FILLED for a simulated
    immediate fill.

    SCOPED DOWN (S-5, F-16): the intermediate routing states §10.7.4 lists
    between VALIDATED and FILLED — PENDING, ROUTED, ACKNOWLEDGED — and the
    PARTIALLY_FILLED / CANCELLED / EXPIRED states are NOT modeled: they
    presuppose a broker/venue round-trip and partial-fill/TIF machinery that
    S-5 excludes (simulated immediate full fill has no routing round-trip).
    Transition enforcement (§10.7.4 "Invalid transitions shall be rejected")
    IS applied at the persistence layer for the transitions that exist
    (guarded UPDATE ... WHERE status = <expected>), but this enum does not
    encode a full state-machine graph.
    """

    CREATED = "CREATED"
    VALIDATED = "VALIDATED"
    REJECTED = "REJECTED"
    FILLED = "FILLED"


@dataclass(frozen=True)
class TargetPosition:
    """The target this order should move the portfolio toward — the §11.2
    Construction output (target_weight) plus the price needed to convert it
    to units.

    `reference_price` is the price used to translate a currency/weight target
    into instrument units (§10.6.5 "Order Quantity computed considering ...").
    It is a REQUIRED INPUT here, not fetched: Order Generation is pure,
    deterministic computation (P-13), so the caller supplies the price it
    priced the target against (Step 3.3's live demo wires it to a real
    Binance last price via the Step 3.0 CCXT connector). This mirrors why
    Sizing takes its volatility forecast as an input rather than computing it
    (domain/portfolio/sizing.py).

    target_notional / target_quantity are DERIVED (deterministic) rather than
    stored, so a TargetPosition cannot hold an internally-inconsistent
    weight/notional/quantity triple.
    """

    asset: AssetRef
    target_weight: Decimal      # signed portfolio weight from §11.2 Construction
    portfolio_value: Decimal    # AUM the weight is denominated against
    reference_price: Decimal    # price used to convert notional -> units (> 0)

    @property
    def target_notional(self) -> Decimal:
        """Signed target currency exposure = target_weight x portfolio_value."""
        return self.target_weight * self.portfolio_value

    @property
    def target_quantity(self) -> Decimal:
        """Signed target position in instrument units = target_notional / price.

        NOT rounded here — rounding to the quantity column's scale is Order
        Generation's decision (order_generation.py), kept in one place.
        """
        return self.target_notional / self.reference_price


@dataclass(frozen=True)
class CurrentPosition:
    """Current holding in an instrument — Doc 14 §10.6.6 "Current Positions".

    Deliberately excluded from Sizing (§11.3) and Construction (§11.2) per the
    boundary flagged in domain/portfolio/sizing.py ("current/existing position
    ... enters at Step 3.3 (Order Generation), not here"): a target is an
    ABSOLUTE position; converting it to an order requires the current position
    as a delta, which §10.6.5 ("Order Quantity computed considering current
    positions") owns.

    `quantity` is signed (positive = net long, negative = net short, 0 = flat)
    and read from core.positions (NUMERIC(28,8) after Step 3.0). A flat/absent
    position is represented as quantity=0.
    """

    asset: AssetRef
    quantity: Decimal


@dataclass(frozen=True)
class OrderIntent:
    """A computed, not-yet-persisted order — the §10.7.3 Order Model, minus the
    fields the datastore assigns (id, status default, timestamps).

    Immutable per P-2/§10.7 ("Orders shall be registered as governed
    artifacts"). Produced by order_generation.compute_order_intent and handed
    to OrderRepository.create for the first real core.orders write.

    Carries the pre-persistence audit trail (§10.7.10 "Order Audit Trail"):
    target_quantity/current_quantity/delta_quantity make the §10.6.5 quantity
    derivation reproducible from the stored order rather than opaque.

    LINEAGE (F-13, resolved by migration d1f8b6c4a7e2): §10.6.5 requires
    "complete lineage to the originating signal" and §10.7.3 lists a "Signal
    Reference" field. `signal_id` is persisted into a dedicated, FK-enforced
    core.orders.signal_id column (REFERENCES core.signals(id), nullable — a
    manually-placed or non-signal-originated order legitimately has none).
    `correlation_id` is NOT used for this — it is left free for its own
    established platform meaning (request/event tracing, Doc 10 §6/§8).
    """

    idempotency_key: UUID        # client-generated UUID v7 (§10.7.5)
    portfolio_id: UUID
    strategy_id: UUID | None
    asset: AssetRef
    side: OrderSide
    quantity: Decimal            # ABSOLUTE order size in units, > 0
    order_type: OrderType
    time_in_force: TimeInForce
    reference_price: Decimal     # price the target was converted against (audit)
    target_quantity: Decimal     # signed absolute target (audit)
    current_quantity: Decimal    # signed current holding (audit)
    delta_quantity: Decimal      # signed target - current == +/- quantity (audit)
    signal_id: UUID | None       # originating signal lineage (-> core.orders.signal_id)


@dataclass(frozen=True)
class RecordedOrder:
    """A persisted order — the datastore-assigned current-state view.

    Returned by OrderRepository.create AND by the lifecycle transitions
    (mark_validated/mark_rejected/mark_filled), so it reflects the order's
    CURRENT state, not only its creation. Echoes the intent plus the
    DB-assigned id, status, and created_at.

    FILL OUTCOME (`filled_quantity`, `average_price`) added in Step 4.4
    (Execution Vertical Slice), the first READ consumer of core.orders
    (GET /v1/portfolios/{id}/orders — the blotter). They are canonical §10.7.3
    Order Model fields already persisted (Step 1.1 schema; quantity columns
    NUMERIC after Step 3.0): `filled_quantity` is 0 and `average_price` is None
    until a fill lands, then set by mark_filled (§10.8.6). Additive with
    defaults so no existing constructor (the Step 3.3/3.5 write path) breaks —
    this closes a latent gap where a mark_filled result could not express the
    very fill price/quantity it had just written. Judgment call flagged in the
    Step 4.4 report.
    """

    id: UUID
    idempotency_key: UUID
    portfolio_id: UUID
    strategy_id: UUID | None
    asset_id: UUID
    side: OrderSide
    quantity: Decimal
    order_type: OrderType
    time_in_force: TimeInForce
    status: OrderStatus
    signal_id: UUID | None
    created_at: object  # datetime; typed loosely to avoid a datetime import in the value layer
    filled_quantity: Decimal = Decimal("0")  # units filled so far (§10.7.3); 0 until a fill
    average_price: Decimal | None = None      # VWAP fill price (§10.7.3); None until a fill


@dataclass(frozen=True)
class Fill:
    """A simulated execution fill — Doc 14 §10.8.6 (Fill Handling), the input
    to trade recording (§10.9.4) and position update (§10.6.6).

    Step 3.5 (S-5, F-16): produced by the SIMULATED fill engine
    (domain/execution/simulation.py) — a full fill of the order's quantity at
    the supplied market price, zero commission, venue "SIM". No slippage,
    partial-fill, or liquidity model (deferred per S-5's paper-trading
    exclusion). `quantity` is the ABSOLUTE fill size (> 0); direction is `side`.
    Immutable per P-2 (§10.8.6 "Every fill produces immutable record per P-5").
    """

    order_id: UUID
    portfolio_id: UUID
    asset_id: UUID               # resolved instrument id (matches RecordedOrder)
    side: OrderSide
    quantity: Decimal            # absolute fill size in units, > 0
    price: Decimal               # execution price
    commission: Decimal          # 0 in Step 3.5 (S-5, F-16)
    venue: str                   # "SIM" — no real broker/venue (S-5)
    executed_at: object          # datetime; typed loosely per this module's convention
    realized_pnl: Decimal = Decimal("0")  # this fill's realized P&L (0 for pure opens/adds)

    @property
    def signed_quantity(self) -> Decimal:
        """Signed position delta this fill applies (+ BUY, − SELL)."""
        return self.quantity if self.side is OrderSide.BUY else -self.quantity

    @property
    def gross_notional(self) -> Decimal:
        """Absolute traded notional = quantity × price (commission separate)."""
        return self.quantity * self.price


@dataclass(frozen=True)
class RecordedExecution:
    """A persisted execution — the core.executions view of a Fill (§10.9.4
    Trade Recording). Returned by ExecutionRepository.record.

    `net_amount` is the signed cash effect of the trade (§10.9.4): negative
    for a BUY (cash out), positive for a SELL (cash in), commission included.
    Immutable per P-2/§10.9.4 ("Trade records shall be immutable after
    recording. Corrections shall create adjusting entries").
    """

    id: UUID
    order_id: UUID
    portfolio_id: UUID
    asset_id: UUID
    side: OrderSide
    quantity: Decimal
    price: Decimal
    commission: Decimal
    net_amount: Decimal
    venue: str
    executed_at: object
    created_at: object
    realized_pnl: Decimal | None = None  # this fill's realized P&L; NULL only for pre-migration rows never backfilled
    # Backtest trade-result fields (Engine TP/SL step) — populated ONLY on the
    # CLOSING fill of a backtest trade (TP/SL/END_OF_DATA exit); NULL on an
    # entry fill and on every live/paper execution, which has no TP/SL concept.
    price_return_pct: Decimal | None = None  # (exit-entry)/entry*100, signed to match trade direction
    market_move_pct: Decimal | None = None   # same formula, unsigned magnitude
    exit_reason: str | None = None           # "TP_HIT" | "SL_HIT" | "END_OF_DATA"

# Governing specification: Doc 15 §11.3 — Position Sizing Architecture
# Layer: Domain — Doc 07 §Layers (contract + value objects; no persistence, no I/O)
# Invariants: P-1 (methodology external), P-13 (deterministic sizing), Port-2 (risk-managed deployment)
# Scope: handbook/KNOWN_LIMITATIONS.md S-5 (Phase 3A scoped-down)
# Per Doc 00 §14.11
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from types import MappingProxyType
from typing import Mapping

from quant_hub.domain.market_data.entities import AssetRef
from quant_hub.domain.strategy_engine.entities import Signal


@dataclass(frozen=True)
class SizingContext:
    """Inputs a position-sizing methodology receives — Doc 15 §11.3.3 "Input Parameters".

    ── PROPOSED CONTRACT FILLING/SCOPING A NAMED SPEC (Doc 00 §14.5/§14.7) ──
    Flagged, not silently invented. §11.3.3 names the Input Parameters as
    "Signal strength, volatility forecast, correlation matrix, risk budget
    allocation, capital allocation". This context is the SCOPED-DOWN subset
    (S-5) needed to convert one signal into one instrument's target size:

      signal            §11.3.3 "Signal strength" — the conviction to size.
                        Reuses the Phase 2 Signal (Signal.value ∈ [-1, 1],
                        signed conviction, Step 2.2) rather than a parallel
                        "signal strength" scalar — not redefining an existing
                        platform concept (Doc 00 §14.6).
      portfolio_value   §11.3.3 "capital allocation" + §11.3.4 "Maximum
                        Position ... as percentage of portfolio value" — the
                        AUM the sizing and its max-position cap are relative
                        to. This is the "current portfolio value" a sizer
                        needs beyond the Signal.
      volatility        §11.3.3 "volatility forecast" + §11.3.4 "Volatility
                        Targeting". OPTIONAL — only vol-targeting
                        methodologies use it; a pure conviction-scaling
                        methodology ignores it. A forecast passed IN (§11.3.3
                        makes it an input, not something sizing computes).
      config            The external methodology parameters per P-1 (§11.3.1
                        "methodology shall be external to platform"; §11.3.3
                        "Sizing Methodology ... custom"). Opaque, never
                        interpreted by platform code — same treatment as a
                        strategy's config (Step 2.3) and Signal.metadata.

    ── DELIBERATELY OMITTED, flagged (not oversights) ──────────────────────
      current/existing position — NOT a sizing input. §11.3.3's Output is a
        "Target position size per instrument" (an ABSOLUTE target). Turning a
        target into an order requires the current position as a delta, but
        that delta computation is Doc 14 §10.6.5 Order Generation's job
        ("order quantity computation"), NOT sizing's — §11.3.7 explicitly
        hands sizing's output TO §10.6.5. Including current_position here
        would blur the §11.3 / §10.6.5 boundary the docs draw. It enters at
        Step 3.3 (Order Generation), not here. (The one §11.3.5 item that
        WOULD need current state — "Drawdown-Based Adjustment" — is scoped
        out per S-5; see SizingConstraints.)
      correlation matrix — §11.3.3 input, but multi-instrument /
        correlation-aware sizing (§11.3.4 "Correlation-Aware Sizing") is
        out of Phase 3A scope per S-5 (single-instrument sizing only).
    """

    signal: Signal
    portfolio_value: Decimal
    volatility: Decimal | None = None
    config: Mapping[str, object] = field(default_factory=lambda: MappingProxyType({}))


@dataclass(frozen=True)
class SizingConstraints:
    """Platform-governed sizing constraints — Doc 15 §11.3.4 / §11.3.5.

    These are PLATFORM-owned safety bounds, NOT methodology config: §11.3.4
    states the constraint table's values "represent platform safety bounds —
    strategies may configure tighter limits but shall not exceed these
    maximums", and §11.3.1 requires "position sizes shall be constrained by
    risk budgets, not just conviction". So the clamp lives with the platform
    (PositionSizingService), separate from the external methodology (P-1) —
    the same platform-owned-gate / plugin-owned-computation split as Step
    2.2's Signal Validation vs. Signal Combination.

    SCOPED DOWN (S-5): only "Maximum Position — as percentage of portfolio
    value" (§11.3.4, the "Single Instrument Max" row of the §11.3.4 table,
    which the doc defaults to 5% of AUM) is implemented. The rest of §11.3.5
    — sector max, liquidity/ADV constraints, concentration (HHI), leverage
    limits, drawdown-based adjustment — are explicitly DEFERRED per S-5
    (they require multi-instrument state, market-microstructure data, or
    portfolio-level aggregation none of which the Phase 3A single-instrument
    slice has). `max_position_pct` is caller-supplied (not hardcoded to the
    doc's 5%) so the platform default vs. a strategy's tighter choice stays a
    governance decision, not a code constant.
    """

    max_position_pct: Decimal  # max |position| as a fraction of portfolio_value (e.g. 0.05 = 5% of AUM)


@dataclass(frozen=True)
class PositionSizingDecision:
    """Output of position sizing — Doc 15 §11.3.3 "Output: Target position size per instrument".

    JUDGMENT CALL (Doc 00 §14.5/§14.7 — flagged): `target_notional` is a
    signed CURRENCY exposure (target notional value), NOT a quantity in
    instrument units. §11.3.4's constraints are all expressed in currency
    ("percentage of portfolio value"/AUM), and Doc 14 §10.6.5 Order
    Generation explicitly owns "order quantity computation" (notional →
    units, which needs a price). Keeping sizing in the notional/risk domain
    and deferring unit-conversion to §10.6.5 is the cleanest reading of the
    §11.3.7 → §10.6.5 handoff; it also means sizing needs no price input.
    Sign follows the conviction: positive = long target, negative = short.

    Carries `raw_notional` and `constrained` (the pre-clamp methodology
    output and whether the platform cap bound) as the seed of §11.3.9's
    "constraint compliance report" artifact. Immutable per §11.3.9/P-2.
    """

    asset: AssetRef
    target_notional: Decimal   # signed, post-constraint (the actionable target)
    raw_notional: Decimal      # signed, pre-constraint (methodology output, for audit)
    constrained: bool          # True if the max-position cap bound the raw size
    portfolio_value: Decimal


class PositionSizer(ABC):
    """External position-sizing methodology — Doc 15 §11.3, P-1.

    The METHODOLOGY (how conviction becomes a raw target size) is external
    to the platform per P-1 (§11.3.1: "methodology shall be external to
    platform"; §11.3.3 lists "volatility targeting, Kelly criterion, risk
    parity, equal weight, or custom" — all external). A concrete sizer plugs
    in here, exactly as a Strategy plugs into the Strategy contract (Step
    2.1). The platform provides the MECHANISM (running the methodology, then
    applying platform-governed constraints — PositionSizingService), never a
    specific formula.

    `size` returns the RAW (pre-constraint) signed target notional. Constraint
    application is deliberately NOT the methodology's responsibility — the
    platform clamps afterward (§11.3.1 "conviction shall not override risk
    constraints"), so a methodology cannot exceed a platform safety bound
    even by accident.

    JUDGMENT CALL (flagged): `size` is SYNC, not async — a deliberate
    deviation from the codebase's async-by-default convention (e.g.
    Strategy.generate_signals is async). Position sizing is pure,
    deterministic computation with no I/O (§11.3.10 "deterministic per
    P-13"; §11.3.3 makes every input — incl. the volatility forecast — a
    passed-in parameter, so the methodology fetches nothing). Sync makes the
    no-I/O, deterministic nature explicit and the method trivially testable.
    """

    @abstractmethod
    def size(self, context: SizingContext) -> Decimal:
        """Compute the raw (pre-constraint) signed target notional from a SizingContext.

        Deterministic per §11.3.10/P-13: identical context → identical output.
        """
        ...

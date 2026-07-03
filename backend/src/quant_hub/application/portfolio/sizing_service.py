# Governing specification: Doc 15 §11.3 — Position Sizing Architecture
#   §11.3.1 (conviction shall not override risk constraints),
#   §11.3.4 (platform safety bounds), §11.3.10 (deterministic per P-13)
# Layer: Application — Doc 07 §Layers
# Invariants: P-1 (methodology external), P-13 (determinism), Port-2 (risk-managed deployment)
# Scope: handbook/KNOWN_LIMITATIONS.md S-5
# Per Doc 00 §14.11
from __future__ import annotations

from quant_hub.domain.portfolio.sizing import (
    PositionSizer,
    PositionSizingDecision,
    SizingConstraints,
    SizingContext,
)


class PositionSizingService:
    """The platform MECHANISM for position sizing — Doc 15 §11.3.

    Runs an external methodology (PositionSizer, P-1) to get a raw target,
    then applies the platform-governed constraint clamp (§11.3.4 safety
    bounds). This is the enforcement point for §11.3.1's "position sizes
    shall be constrained by risk budgets, not just conviction" and Port-2
    Risk-Managed Capital Deployment — the methodology CANNOT exceed a
    platform cap, because the clamp runs after it and is not the
    methodology's to skip. Same platform-owned-gate / plugin-owned-
    computation split as Step 2.2 (Signal Validation gates Signal
    Combination).

    Pure, deterministic (§11.3.10/P-13), no writes — Step 3.1 is a
    computation stage only; persisting sizing decisions as immutable
    artifacts (§11.3.9) comes with a later step that has a consumer.

    Sync (not async): no I/O — see PositionSizer.size's docstring.
    """

    def size_position(
        self,
        sizer: PositionSizer,
        context: SizingContext,
        constraints: SizingConstraints,
    ) -> PositionSizingDecision:
        """Size one instrument: methodology → governed max-position clamp.

        The cap is `max_position_pct × portfolio_value` (§11.3.4 "Maximum
        Position ... as percentage of portfolio value"), applied to the
        MAGNITUDE with the sign preserved — a short target (negative
        conviction) is clamped symmetrically, so the risk bound holds
        regardless of direction.
        """
        raw = sizer.size(context)
        cap = constraints.max_position_pct * context.portfolio_value

        if raw > cap:
            target, constrained = cap, True
        elif raw < -cap:
            target, constrained = -cap, True
        else:
            target, constrained = raw, False

        return PositionSizingDecision(
            asset=context.asset,
            target_notional=target,
            raw_notional=raw,
            constrained=constrained,
            portfolio_value=context.portfolio_value,
        )

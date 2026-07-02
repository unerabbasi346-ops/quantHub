# Governing specification: Doc 15 §11.3.4 (Risk-Based Sizing: Volatility Targeting,
#   Maximum Position); P-1 (methodology external)
# Layer: Application — Doc 07 §Layers (a PositionSizer methodology; pure computation)
# Per Doc 00 §14.11
#
# Step 3.1: a trivial, textbook reference position-sizing methodology. Its
# ONLY purpose is to prove Doc 15 §11.3's PositionSizer/PositionSizingService
# contract is genuinely pluggable — it is not a recommended sizing formula.
#
# P-1 COMPLIANCE (flagged, negation clause per Doc 00 §14.9): linear
# conviction scaling (optionally volatility-targeted) is a generic textbook
# sizing approach — it is NOT modeled on, shaped like, or derived from any
# real strategy this platform is built for (Lancaster or otherwise). Stating
# what it is NOT is exactly the negation P-1 permits.
from __future__ import annotations

from decimal import Decimal

from quant_hub.domain.portfolio.sizing import PositionSizer, SizingContext


class LinearConvictionSizer(PositionSizer):
    """Linear conviction sizing with optional volatility targeting — a reference methodology.

    Raw target notional = conviction × max_fraction × portfolio_value, where
    conviction is Signal.value ∈ [-1, 1] (Step 2.2) and `max_fraction` (from
    the opaque config, P-1) is the notional fraction of AUM targeted at full
    conviction. This is §11.3.4's "Maximum Position ... as percentage of
    portfolio value" applied linearly to conviction.

    If the config carries `target_vol` AND the context supplies a `volatility`
    forecast, the raw size is scaled by (target_vol / volatility) — §11.3.4
    "Volatility Targeting: position size inversely proportional to
    volatility". This can push the raw size ABOVE max_fraction; that is
    intentional and safe — the platform's PositionSizingService clamps it to
    the governed max-position cap afterward (the methodology never enforces
    the cap itself, §11.3.1).

    Config keys (all optional, opaque per P-1 — the platform never inspects
    them; this methodology defines its own):
      - `max_fraction` (default "0.05" — matches Doc 15 §11.3.4's 5%-of-AUM
        single-instrument default, used here only as this methodology's own
        default, not a platform constant)
      - `target_vol`   (optional; enables volatility targeting when the
        context also provides `volatility`)
    """

    def size(self, context: SizingContext) -> Decimal:
        conviction = context.signal.value  # [-1, 1], signed
        max_fraction = Decimal(str(context.config.get("max_fraction", "0.05")))
        raw = conviction * max_fraction * context.portfolio_value

        target_vol = context.config.get("target_vol")
        if target_vol is not None and context.volatility is not None and context.volatility > 0:
            raw = raw * (Decimal(str(target_vol)) / context.volatility)

        return raw

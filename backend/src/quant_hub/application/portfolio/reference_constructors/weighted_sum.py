# Governing specification: Doc 15 §11.2.4 (Portfolio Construction Methodology —
#   "Custom Methodologies"), §11.2.6 (Multi-Strategy Aggregation — Strategy Weighting)
# Layer: Application — Doc 07 §Layers (a PortfolioConstructor methodology; pure computation)
# Per Doc 00 §14.11
#
# Step 3.2: a trivial, textbook reference construction methodology — a
# weighted sum of constituent strategy contributions. Its ONLY purpose is to
# prove the PortfolioConstructor contract is genuinely pluggable and
# generalizes past single-strategy, per this step's explicit instruction.
# Not a recommended construction methodology (§11.2.4's real methodologies —
# mean-variance, risk parity, Black-Litterman — are all deferred per S-5).
#
# P-1 COMPLIANCE (flagged, negation clause per Doc 00 §14.9): a plain
# weighted sum is the simplest possible aggregation, chosen for the same
# reason as Step 2.4's MA crossover and Step 3.1's linear sizer — generic,
# textbook, not modeled on any real strategy or portfolio methodology this
# platform is built for.
from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from quant_hub.domain.portfolio.construction import (
    PortfolioConstructionResult,
    PortfolioConstructor,
    StrategyContribution,
)


class WeightedSumConstructor(PortfolioConstructor):
    """target_weight = Σ(strategy_weight_i × signal_i.value).

    Aggregates each constituent strategy's signed conviction (Signal.value,
    Step 2.2), weighted by its governed strategy_weight, into one portfolio
    target weight — the §11.2.4 construction output that Position Sizing
    (Step 3.1) then converts into an actionable size (§11.3.1 order).

    With exactly one constituent strategy at strategy_weight=1 (today's only
    exercisable case — Step 2.4's reference strategy), this collapses to
    target_weight = signal.value — the raw conviction passed straight through
    as the portfolio weight. With N>1 contributions it generalizes to a
    genuine weighted aggregation (exercised only by synthetic test data today).

    KNOWN SIMPLIFICATION (flagged; see PortfolioConstructionResult's docstring):
    the result is the raw signed conviction aggregate, NOT normalized to sum
    to 1 across the portfolio — a real optimization-based methodology (§11.2.4)
    must add normalization explicitly; it does not exist here.

    Sizing/capital note (F-12): this constructor is dimensionless — it needs no
    portfolio_value (capital enters downstream at Position Sizing, §11.3.3).
    The pre-inversion version consumed already-sized PositionSizingDecision
    outputs and divided by portfolio_value; post-inversion it consumes raw
    convictions, per the doc-correct Construction-before-Sizing order.
    """

    def construct(self, contributions: Sequence[StrategyContribution]) -> PortfolioConstructionResult:
        if not contributions:
            raise ValueError("construct() requires at least one contribution")

        asset = contributions[0].signal.asset
        target_weight: Decimal = sum(
            (c.strategy_weight * c.signal.value for c in contributions),
            start=Decimal("0"),
        )

        return PortfolioConstructionResult(
            asset=asset,
            target_weight=target_weight,
            contributions=tuple(contributions),
        )

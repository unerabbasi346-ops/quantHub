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
    """target_weight = Σ(strategy_weight_i × target_notional_i) / portfolio_value.

    With exactly one constituent strategy at strategy_weight=1 (today's only
    exercisable case — Step 2.4's reference strategy), this collapses
    exactly to target_weight = target_notional / portfolio_value — the
    identity transform Step 3.1's PositionSizingDecision already implies.
    With N>1 contributions it generalizes to a genuine weighted aggregation
    (exercised only by synthetic test data today, per this step's scope —
    see the flagged pipeline-ordering divergence in domain/portfolio/
    construction.py's module docstring for why this doesn't yet reflect
    Doc 15's real multi-strategy construction methodology).

    JUDGMENT CALL (flagged): requires all contributions to share the same
    `portfolio_value` (raises ValueError otherwise) — §11.2.3's Portfolio
    Model implies one portfolio has one AUM at construction time; mixing
    contributions computed against different portfolio_value snapshots
    would silently produce a meaningless weight. Not stated explicitly by
    §11.2, but the only sound reading given target_weight is denominated in
    a single portfolio_value.
    """

    def construct(self, contributions: Sequence[StrategyContribution]) -> PortfolioConstructionResult:
        if not contributions:
            raise ValueError("construct() requires at least one contribution")

        asset = contributions[0].decision.asset
        portfolio_value = contributions[0].decision.portfolio_value
        for c in contributions:
            if c.decision.portfolio_value != portfolio_value:
                raise ValueError(
                    "all contributions must share the same portfolio_value "
                    f"(got {c.decision.portfolio_value} and {portfolio_value})"
                )

        weighted_notional: Decimal = sum(
            (c.strategy_weight * c.decision.target_notional for c in contributions),
            start=Decimal("0"),
        )
        target_weight = weighted_notional / portfolio_value

        return PortfolioConstructionResult(
            asset=asset,
            target_weight=target_weight,
            portfolio_value=portfolio_value,
            contributions=tuple(contributions),
        )

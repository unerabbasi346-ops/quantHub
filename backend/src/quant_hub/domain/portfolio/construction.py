# Governing specification: Doc 15 §11.2 — Portfolio Construction Architecture
# Layer: Domain — Doc 07 §Layers (contract + value objects; no persistence, no I/O)
# Invariants: P-1 (methodology external), P-9/Port-1 (Portfolio Construction Separation),
#             P-13 (reproducibility)
# Scope: handbook/KNOWN_LIMITATIONS.md S-5 (Phase 3A scoped-down)
# Per Doc 00 §14.11
#
# ── FLAGGED PIPELINE-ORDERING DIVERGENCE (Doc 00 §14.5/§14.7 — reported, not
# silently resolved) ──────────────────────────────────────────────────────
# Doc 15's OWN text states the pipeline order is Construction -> weights ->
# Sizing -> position sizes:
#   §11.3.1: "Portfolio construction produces target weights or exposures;
#     position sizing converts these into actionable position sizes."
#   §11.2.12: "Portfolio construction shall integrate with Position Sizing
#     (Section 11.3 — portfolio weights feed into position sizing)."
# This module does the OPPOSITE: it consumes Step 3.1's ALREADY-SIZED
# PositionSizingDecision outputs (target_notional) and aggregates them into
# a portfolio-level weight — per this step's explicit instruction. This is
# a deliberate, instructed deviation from Doc 15's literal ordering, judged
# acceptable ONLY under S-5's single-reference-strategy scope: with exactly
# one constituent strategy, "aggregate sized positions into a weight" and
# "aggregate weights into a portfolio, then size" are computationally
# equivalent (aggregating one strategy's contribution is the identity
# function either way — see EqualWeightPassThroughConstructor). It does NOT
# generalize once real multi-strategy, weight-based construction (mean-
# variance optimization, risk parity, etc., §11.2.4) is built — at that
# point the correct doc order (Construction before Sizing) would need this
# module's relationship to Step 3.1 to be inverted, which is a future
# phase-boundary decision, not resolved here.
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from quant_hub.domain.market_data.entities import AssetRef
from quant_hub.domain.portfolio.sizing import PositionSizingDecision


@dataclass(frozen=True)
class StrategyContribution:
    """One constituent strategy's sized position — the input this Phase 3A
    pass-through aggregates. Doc 15 §11.2.6 "Strategy Weighting: Weight
    assigned to each constituent strategy within the portfolio."

    A distinct type from PositionSizingDecision (Step 3.1) rather than
    reusing it directly — decouples Construction's contract from Sizing's:
    Doc 15 §11.2.4's real input (a per-strategy target, from whatever
    construction methodology or upstream stage produced it) need not always
    be exactly this codebase's PositionSizingDecision. `decision` embeds it
    for Phase 3A's scoped pass-through use.

    JUDGMENT CALL (flagged): `strategy_weight` is caller-supplied, NOT
    normalized by this type or by the constructor — §11.2.6 names "Strategy
    Weighting" as a governed input but does not mandate weights sum to 1.
    With today's single reference strategy, callers pass weight=1 (see
    EqualWeightPassThroughConstructor); real multi-strategy normalization
    policy (sum-to-1 vs. independent risk budgets, §11.4 Capital Allocation
    territory) is deferred per S-5.
    """

    strategy_id: UUID
    strategy_weight: Decimal
    decision: PositionSizingDecision


@dataclass(frozen=True)
class PortfolioConstructionResult:
    """Output of portfolio construction — Doc 15 §11.2.4 "Output Specification:
    Standardized output: target weights per strategy and per instrument."

    `target_weight` is a fraction of `portfolio_value` (signed — negative
    for a net-short portfolio-level target), NOT a currency amount, per
    §11.2.4's "target weights" language (distinct from Step 3.1's
    currency-denominated target_notional).

    `contributions` preserves every constituent StrategyContribution that
    fed this result — Doc 15 §11.2.6 "Aggregation Transparency: Contribution
    of each strategy to overall portfolio weights ... visible" — and is the
    seed of §11.2.10's "constructed portfolio weights ... construction
    methodology snapshot" artifact (not persisted this step — no writes,
    per this step's explicit scope).

    Immutable per §11.2.10/P-2.
    """

    asset: AssetRef
    target_weight: Decimal
    portfolio_value: Decimal
    contributions: tuple[StrategyContribution, ...]


class PortfolioConstructor(ABC):
    """External construction methodology — Doc 15 §11.2.4, P-1.

    §11.2.1: "Construction methodology shall be external to the platform per
    P-1 — the platform shall govern the methodology framework without
    prescribing specific optimization approaches." §11.2.4 lists mean-
    variance optimization, risk parity, factor-based, Black-Litterman, and
    custom as pluggable methodologies — exactly mirroring PositionSizer's
    (Step 3.1) role for sizing methodology. A concrete constructor plugs in
    here.

    INTERFACE DESIGNED TO GENERALIZE BEYOND SINGLE-STRATEGY (per this
    step's explicit instruction), even though only one reference strategy
    (Step 2.4) exists to exercise it today: `construct` takes a SEQUENCE of
    StrategyContribution, not a single one, so a real multi-strategy
    methodology (mean-variance, risk parity, §11.2.4) can be plugged in
    later without changing this contract — only EqualWeightPassThroughConstructor
    (the reference implementation) is scoped to behave correctly for N=1.

    JUDGMENT CALL: `construct` is SYNC, not async — same reasoning as
    PositionSizer.size (Step 3.1): pure, deterministic computation
    (§11.2.11/P-13 "identical strategy positions, methodology configuration,
    constraints, and market data shall produce identical portfolio
    weights"), no I/O, every input passed in as a parameter.
    """

    @abstractmethod
    def construct(self, contributions: Sequence[StrategyContribution]) -> PortfolioConstructionResult:
        """Aggregate constituent strategy contributions (same instrument) into one
        portfolio-level target weight. Deterministic per §11.2.11/P-13."""
        ...

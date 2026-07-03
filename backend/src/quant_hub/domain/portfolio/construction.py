# Governing specification: Doc 15 §11.2 — Portfolio Construction Architecture
# Layer: Domain — Doc 07 §Layers (contract + value objects; no persistence, no I/O)
# Invariants: P-1 (methodology external), P-9/Port-1 (Portfolio Construction Separation),
#             P-13 (reproducibility)
# Scope: handbook/KNOWN_LIMITATIONS.md S-5 (Phase 3A scoped-down)
# Per Doc 00 §14.11
#
# PIPELINE ORDER (Doc 15 §11.3.1 / §11.2.12 — as built after the F-12 inversion):
# Portfolio Construction runs FIRST and produces target *weights* from
# constituent strategy signals; Position Sizing (Step 3.1,
# domain/portfolio/sizing.py) then consumes those weights and converts them
# into actionable position sizes.
#   §11.3.1: "Portfolio construction produces target weights or exposures;
#     position sizing converts these into actionable position sizes."
#   §11.2.12: "Portfolio construction shall integrate with Position Sizing
#     (Section 11.3 — portfolio weights feed into position sizing)."
# Steps 3.1/3.2 were originally built in the REVERSE order (Sizing -> Construction,
# construction consuming an already-sized PositionSizingDecision) and inverted
# here to match the doc's specified order — see handbook/KNOWN_LIMITATIONS.md
# F-12 (RESOLVED). The inversion is behaviour-preserving for the current N=1
# reference case (verified: identical fills/positions/reproducibility hash).
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from quant_hub.domain.market_data.entities import AssetRef
from quant_hub.domain.strategy_engine.entities import Signal


@dataclass(frozen=True)
class StrategyContribution:
    """One constituent strategy's signed conviction for an instrument — the
    input portfolio construction aggregates. Doc 15 §11.2.6 "Strategy
    Weighting: Weight assigned to each constituent strategy within the
    portfolio."

    Carries the strategy's raw `signal` (Signal.value ∈ [-1, 1], the signed
    conviction from Step 2.2) plus the governed `strategy_weight` — NOT an
    already-sized position. Construction consumes convictions and produces a
    portfolio weight; Position Sizing (Step 3.1) then converts that weight into
    an actionable size (§11.3.1). This is the doc-correct handoff direction
    (F-12 inversion — the pre-inversion contract carried a PositionSizingDecision).

    JUDGMENT CALL (flagged): `strategy_weight` is caller-supplied, NOT
    normalized by this type or by the constructor — §11.2.6 names "Strategy
    Weighting" as a governed input but does not mandate weights sum to 1.
    With today's single reference strategy, callers pass weight=1; real
    multi-strategy normalization policy (sum-to-1 vs. independent risk
    budgets, §11.4 Capital Allocation territory) is deferred per S-5.
    """

    strategy_id: UUID
    strategy_weight: Decimal
    signal: Signal


@dataclass(frozen=True)
class PortfolioConstructionResult:
    """Output of portfolio construction — Doc 15 §11.2.4 "Output Specification:
    Standardized output: target weights per strategy and per instrument."

    `target_weight` is a signed fraction (negative for a net-short target),
    per §11.2.4's "target weights" language — dimensionless, NOT a currency
    amount. Portfolio value / capital enters downstream at Position Sizing
    (§11.3.3 "capital allocation"), not here, so this result carries no
    portfolio_value.

    ── KNOWN SIMPLIFICATION, flagged (Doc 00 §14.5/§14.7 — not an oversight) ──
    Under the current reference methodology (WeightedSumConstructor — the only
    PortfolioConstructor that exists), `target_weight` is the RAW signed
    conviction aggregate Σ(strategy_weight_i × signal_i.value), whose magnitude
    ranges up to Σ|strategy_weight| (e.g. ±1 for the single N=1, weight=1
    strategy). It is **NOT normalized to sum to 1** across the portfolio, and
    no normalization step exists in the platform today. A future N>1 or real
    optimization-based Construction methodology (§11.2.4 — mean-variance, risk
    parity, Black-Litterman) that assumes normalized-to-1 portfolio weights
    MUST add that normalization explicitly; it cannot assume it already exists
    here. This holds ONLY for the current reference methodology and is recorded
    so a later implementer does not silently rely on normalization.

    `contributions` preserves every constituent StrategyContribution that fed
    this result — Doc 15 §11.2.6 "Aggregation Transparency: Contribution of
    each strategy to overall portfolio weights ... visible" — and seeds
    §11.2.10's "construction methodology snapshot" artifact (not persisted this
    step — no writes). Immutable per §11.2.10/P-2.
    """

    asset: AssetRef
    target_weight: Decimal
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

    INTERFACE DESIGNED TO GENERALIZE BEYOND SINGLE-STRATEGY (per this step's
    explicit instruction), even though only one reference strategy (Step 2.4)
    exists to exercise it today: `construct` takes a SEQUENCE of
    StrategyContribution, not a single one, so a real multi-strategy
    methodology (mean-variance, risk parity, §11.2.4) can be plugged in later
    without changing this contract — only WeightedSumConstructor (the
    reference implementation) is scoped to behave correctly for N=1.

    JUDGMENT CALL: `construct` is SYNC, not async — same reasoning as
    PositionSizer.size (Step 3.1): pure, deterministic computation
    (§11.2.11/P-13 "identical strategy signals, methodology configuration,
    constraints, and market data shall produce identical portfolio weights"),
    no I/O, every input passed in as a parameter.
    """

    @abstractmethod
    def construct(self, contributions: Sequence[StrategyContribution]) -> PortfolioConstructionResult:
        """Aggregate constituent strategy convictions (same instrument) into one
        portfolio-level target weight. Deterministic per §11.2.11/P-13."""
        ...

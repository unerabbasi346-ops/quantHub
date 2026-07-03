# Governing specification: Doc 15 §11.2 — Portfolio Construction Architecture
# Layer: Application — Doc 07 §Layers
# Invariants: P-1 (methodology external), P-13 (reproducibility)
# Scope: handbook/KNOWN_LIMITATIONS.md S-5
# Per Doc 00 §14.11
#
# SCOPE (S-5, flagged — most of §11.2 beyond basic aggregation is deferred):
# this service is a THIN pass-through — group contributions by instrument,
# run the external methodology per instrument. It does NOT implement:
#   - §11.2.5 Constraint Modeling (risk/position/turnover/liquidity/
#     regulatory constraints, "Constraint violations ... may prevent
#     construction completion") — no portfolio-level constraint clamp exists
#     in this step, unlike Step 3.1's PositionSizingService which DOES clamp.
#     Step 3.1's per-instrument cap already bounds each contribution before
#     it reaches here; a portfolio-level check (e.g. aggregate gross
#     exposure) is new machinery not built here.
#   - §11.2.6's "Cross-Strategy Correlation" / "Diversification Assessment"
#     — requires multi-strategy return history that doesn't exist with one
#     reference strategy.
#   - §11.2.7 Portfolio Optimization (mean-variance, solver timeout/fallback
#     table) — explicitly "optional" per §11.2.7 itself; not exercised.
#   - §11.2.8 Benchmark Tracking, §11.2.9 Governance approval workflow,
#     §11.2.10 artifact persistence (no writes this step).
# All deferred per S-5's "disproportionate for a solo-developer platform's
# current stage" rationale, same discipline as S-1/S-4.
from __future__ import annotations

from quant_hub.domain.portfolio.construction import (
    PortfolioConstructionResult,
    PortfolioConstructor,
    StrategyContribution,
)


class PortfolioConstructionService:
    """The platform MECHANISM for portfolio construction — Doc 15 §11.2.

    Groups contributions by instrument and runs the external methodology
    (PortfolioConstructor, P-1) per instrument. Unlike Step 3.1's
    PositionSizingService, this mechanism applies NO additional platform
    constraint after the methodology runs — see module docstring for what's
    deferred per S-5. The split (external methodology vs. platform
    mechanism) still exists for interface parity with Step 3.1 and to leave
    a clear seam for a future constraint clamp (§11.2.5) without redesigning
    this API.

    Pure, deterministic (§11.2.11/P-13), no writes.
    """

    def construct_portfolio(
        self,
        constructor: PortfolioConstructor,
        contributions: list[StrategyContribution],
    ) -> list[PortfolioConstructionResult]:
        """Aggregate contributions across possibly-multiple instruments into
        one PortfolioConstructionResult per instrument.

        Grouping key is (symbol, exchange) — AssetRef is not hashable-safe
        across incidental field differences (e.g. `name`), so the natural
        key (Step 1.1/1.3 precedent: assets_symbol_exchange_uq) is used.
        """
        by_asset: dict[tuple[str, str], list[StrategyContribution]] = {}
        for contribution in contributions:
            asset = contribution.signal.asset
            key = (asset.symbol, asset.exchange)
            by_asset.setdefault(key, []).append(contribution)

        return [constructor.construct(group) for group in by_asset.values()]

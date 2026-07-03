# Governing specification: Doc 15 §11.5.3 — Risk Measurement
#                          Doc 15 §11.5.4 — Risk Models (P-1: methodology external)
#                          Doc 07 — Backend Architecture §Infrastructure Layer
# Layer: Infrastructure — Doc 07 §Layers
# Invariants: Port-3 (deterministic), P-1 (model is external config), P-13
# Scope: handbook/KNOWN_LIMITATIONS.md S-5 / F-18
# Per Doc 00 §14.11
#
# Step 3.6: the first REAL RiskModelInterface, replacing StubRiskModel's
# all-zero metrics. Computes exactly the §11.5.3 metrics that are derivable
# from current position + price data ALONE — exposure and leverage. The
# return-history-dependent metrics (VaR, CVaR, volatility, max drawdown, beta)
# are left at zero and flagged (F-18): they require a covariance/factor/
# historical model (§11.5.4, excluded by S-5) fed by a portfolio return series
# / equity curve / benchmark series that this platform does not yet accumulate.
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from quant_hub.domain.portfolio.positions import RecordedPosition
from quant_hub.domain.risk.entities import RiskMetrics
from quant_hub.domain.risk.interfaces import RiskModelInterface

_ZERO = Decimal("0")
# Metrics that require return-series history the platform does not accumulate
# yet — computed as zero and documented rather than faked (F-18).
_DEFERRED_ZERO = _ZERO


class PositionExposureRiskModel(RiskModelInterface):
    """Position-derived exposure & leverage risk model — Doc 15 §11.5.3.

    Deterministic per Port-3: identical positions + equity produce identical
    metrics (pure arithmetic, no randomness, no external calls). Satisfies
    RiskModelInterface per P-1 as the platform's baseline model; a
    covariance/factor/historical model (§11.5.4) can replace it later without
    touching the framework.

    COMPUTED NOW (from position market values):
      gross_exposure = Σ |market_value|
      net_exposure   = Σ  market_value   (signed)
      gross_leverage = gross_exposure / equity
      net_leverage   = net_exposure   / equity
    DEFERRED to zero (F-18 — need return-series history + a §11.5.4 model):
      var_1d_99, cvar_1d_99, volatility_annualized, max_drawdown, beta
    """

    async def compute_metrics(
        self, portfolio_id: UUID, positions: list[object], equity: Decimal
    ) -> RiskMetrics:
        gross_exposure = _ZERO
        net_exposure = _ZERO
        for p in positions:
            assert isinstance(p, RecordedPosition)  # infra consumes the domain view
            mv = p.market_value
            gross_exposure += abs(mv)
            net_exposure += mv

        if equity > _ZERO:
            gross_leverage = gross_exposure / equity
            net_leverage = net_exposure / equity
        else:
            # No positive capital base -> leverage undefined; report 0 rather
            # than divide by zero. (F-18: equity is a caller-supplied input.)
            gross_leverage = _ZERO
            net_leverage = _ZERO

        return RiskMetrics(
            portfolio_id=portfolio_id,
            var_1d_99=_DEFERRED_ZERO,
            cvar_1d_99=_DEFERRED_ZERO,
            volatility_annualized=_DEFERRED_ZERO,
            max_drawdown=_DEFERRED_ZERO,
            beta=_DEFERRED_ZERO,
            gross_exposure=gross_exposure,
            net_exposure=net_exposure,
            gross_leverage=gross_leverage,
            net_leverage=net_leverage,
            computed_at=datetime.now(timezone.utc),
        )

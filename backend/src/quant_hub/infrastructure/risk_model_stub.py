# Governing specification: Doc 15 §11.5.4 — Risk Models
#                          Doc 07 — Backend Architecture §Infrastructure Layer
# Layer: Infrastructure — Doc 07 §Layers
# P-1: risk model methodology is external configuration — this stub satisfies the interface
#      until a real covariance/factor model is configured
# Per Doc 00 §14.11
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from quant_hub.domain.risk.entities import RiskMetrics
from quant_hub.domain.risk.interfaces import RiskModelInterface


class StubRiskModel(RiskModelInterface):
    """Placeholder risk model returning zeroed metrics — Doc 15 §11.5.4.

    Satisfies RiskModelInterface per P-1 (model is external config).
    Returns zero for all metrics — not suitable for production use.
    Replace with a covariance-based or factor-based model in Phase 1.
    Determinism invariant Port-3 is trivially satisfied (zeros are deterministic).
    """

    async def compute_metrics(
        self, portfolio_id: UUID, positions: list[object], equity: Decimal
    ) -> RiskMetrics:
        zero = Decimal("0")
        return RiskMetrics(
            portfolio_id=portfolio_id,
            var_1d_99=zero,
            cvar_1d_99=zero,
            volatility_annualized=zero,
            max_drawdown=zero,
            beta=zero,
            gross_exposure=zero,
            net_exposure=zero,
            gross_leverage=zero,
            net_leverage=zero,
            computed_at=datetime.now(timezone.utc),
        )

# Governing specification: Doc 15 §11.5 — Risk Management Architecture
#                          Doc 02 — System Architecture §Dependency Rules (Risk Engine approves every order)
#                          Doc 07 — Backend Architecture §Application Layer
# Layer: Application — Doc 07 §Layers
# Invariants: Port-3, Port-4, Port-5, P-1, P-2, P-5
# Per Doc 00 §14.11
from __future__ import annotations

from uuid import UUID

from quant_hub.domain.risk.entities import RiskAssessment, RiskLimitStatus, RiskMetrics
from quant_hub.domain.risk.interfaces import (
    RiskAssessmentRepository,
    RiskLimitRepository,
    RiskModelInterface,
    RiskSnapshotRepository,
)


class RiskService:
    """Risk management application service — Doc 15 §11.5 / Doc 07 §Application Layer.

    Responsibilities per Doc 15 §11.5:
    - Pre-trade order assessment (satisfies Doc 02 mandatory risk gate)
    - Portfolio risk metric computation per Port-3 (Deterministic Portfolio State)
    - Continuous limit monitoring per Port-4 (Continuous Risk Monitoring)
    - Portfolio-level limit authority per Port-5 (Strategy Risk Separation)

    All risk evaluation logic is stubbed — real implementation deferred to Phase 1.
    Wire via RiskApprovalAdapter (infrastructure) to satisfy the execution risk gate.
    """

    def __init__(
        self,
        risk_model: RiskModelInterface,           # P-1: model is external config
        limits: RiskLimitRepository,
        assessments: RiskAssessmentRepository,
        snapshots: RiskSnapshotRepository,
    ) -> None:
        self._model = risk_model
        self._limits = limits
        self._assessments = assessments
        self._snapshots = snapshots

    async def assess_pre_trade(self, order: object) -> bool:
        """Pre-trade risk assessment — Doc 02 §Dependency Rules / Doc 15 §11.5.7.

        Portfolio-level limits supersede strategy limits per Port-5.
        Stub: approves all orders. Real limit-checking deferred to Phase 1.
        Returns True if approved, False if rejected.
        """
        return True

    async def compute_portfolio_metrics(
        self, portfolio_id: UUID, positions: list[object]
    ) -> RiskMetrics:
        """Compute portfolio risk metrics — Doc 15 §11.5.3.

        Delegates to the configured RiskModelInterface per P-1 (model is config).
        Deterministic per Port-3: same inputs produce same outputs.
        Stub: delegates to StubRiskModel, returns zeroed metrics.
        """
        return await self._model.compute_metrics(portfolio_id, positions)

    async def check_limits(
        self, portfolio_id: UUID, metrics: RiskMetrics
    ) -> list[object]:
        """Check portfolio metrics against governed limits — Doc 15 §11.5.7/11.5.8.

        Breaches trigger immediate escalation per Port-4.
        Stub: returns empty list (no breaches). Real checking deferred to Phase 1.
        """
        return []

    async def get_latest_assessment(self, portfolio_id: UUID) -> RiskAssessment | None:
        """Retrieve latest risk assessment artifact — Doc 15 §11.5.13.

        Assessments are immutable governed artifacts per P-2 and P-5.
        """
        return await self._assessments.get_latest(portfolio_id)

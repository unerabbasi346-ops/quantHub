# Governing specification: Doc 02 — System Architecture §Dependency Rules
#                          Doc 15 §11.5 — Risk Management Architecture
#                          Doc 07 — Backend Architecture §Infrastructure Layer
# Layer: Infrastructure — Doc 07 §Layers
# Purpose: bridges execution domain's RiskApprovalInterface to the Risk Engine's RiskService
# Doc 02: Risk Engine must approve every order (mandatory pre-trade gate)
# Doc 07 §Dependency Rules: infrastructure implements domain interfaces
# Per Doc 00 §14.11
from __future__ import annotations

from quant_hub.application.risk.service import RiskService
from quant_hub.domain.execution.interfaces import RiskApprovalInterface, RiskDecision


class RiskApprovalAdapter(RiskApprovalInterface):
    """Infrastructure adapter: execution risk gate → Risk Engine service.

    Implements execution domain's RiskApprovalInterface by delegating to
    RiskService (application/risk layer). This is the architectural bridge
    that makes the Risk Engine the authoritative pre-trade gatekeeper per
    Doc 02: "Risk Engine must approve every order."

    Replaces StubRiskApprovalService once the Risk Engine domain is wired.
    StubRiskApprovalService remains available for test environments that
    need to bypass risk evaluation entirely.
    """

    def __init__(self, risk_service: RiskService) -> None:
        self._risk_service = risk_service

    async def evaluate(self, order: object) -> RiskDecision:
        approved = await self._risk_service.assess_pre_trade(order)
        if approved:
            return RiskDecision(approved=True, reason="risk engine: pre-trade assessment passed")
        return RiskDecision(approved=False, reason="risk engine: pre-trade assessment rejected")

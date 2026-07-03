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
from quant_hub.domain.risk.entities import PreTradeRiskRequest


class RiskApprovalAdapter(RiskApprovalInterface):
    """Infrastructure adapter: execution risk gate → Risk Engine service.

    Implements execution domain's RiskApprovalInterface by delegating to
    RiskService.assess_pre_trade (application/risk layer). This is the
    architectural bridge that makes the Risk Engine the authoritative
    pre-trade gatekeeper per Doc 02: "Risk Engine must approve every order."

    Step 3.4: the delegation is now REAL — assess_pre_trade evaluates the
    order against governed limits and can REJECT (Doc 14 §10.7.5). This
    adapter is the production gate; StubRiskApprovalService (always approves)
    is retained for tests only and is never bound in production DI
    (api/dependencies.provide_risk_gate) — the fail-safe posture.

    Expects a PreTradeRiskRequest as the `order` (the §10.7.5 request carries
    price and post-execution context a bare RecordedOrder lacks). A wrong
    input type is a wiring error and is DENIED (fail-closed), not approved.
    """

    def __init__(self, risk_service: RiskService) -> None:
        self._risk_service = risk_service

    async def evaluate(self, order: object) -> RiskDecision:
        if not isinstance(order, PreTradeRiskRequest):
            return RiskDecision(
                approved=False,
                reason=(
                    "risk engine: unassessable order "
                    f"(expected PreTradeRiskRequest, got {type(order).__name__})"
                ),
            )
        result = await self._risk_service.assess_pre_trade(order)
        if result.authorized:
            return RiskDecision(
                approved=True,
                reason=f"risk engine: pre-trade check passed (check_id={result.check_id})",
            )
        return RiskDecision(
            approved=False,
            reason=result.rejection_reason or "risk engine: pre-trade check rejected",
        )

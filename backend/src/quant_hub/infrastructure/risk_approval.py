# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Infrastructure — Doc 07 §Layers
# Doc 02: Risk Engine mandatory pre-trade gate — stub implementation (always approves)
# Per Doc 00 §14.11
from __future__ import annotations

from quant_hub.domain.execution.interfaces import RiskApprovalInterface, RiskDecision


class StubRiskApprovalService(RiskApprovalInterface):
    """Unconditional-approval stub satisfying the Doc 02 mandatory risk gate.

    This implementation always returns approved=True. It exists to wire the
    structural requirement before real risk logic is implemented. Replaced in
    production DI by RiskApprovalAdapter (infrastructure/risk_approval_adapter.py),
    which delegates to the real RiskService built in Step 0.6.

    Retain for test environments that need to bypass risk evaluation entirely.
    Do not use in production — this bypasses all pre-trade risk checks.
    """

    async def evaluate(self, order: object) -> RiskDecision:
        return RiskDecision(approved=True, reason="stub: unconditional approval")

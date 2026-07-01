# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Application — Doc 07 §Layers
# Service: Execution — Doc 07 §Core Services
# Per Doc 00 §14.11
from __future__ import annotations

from quant_hub.domain.execution.interfaces import (
    ExecutionRepository,
    OrderRepository,
    RiskApprovalInterface,
)


class ExecutionService:
    """Application service stub — business logic not implemented in Step 0.4.

    Doc 02: risk_gate is a mandatory constructor dependency. Every order
    submission must call risk_gate.evaluate() before routing. Passing a
    StubRiskApprovalService (always approves) satisfies the structural
    requirement while real risk logic is deferred.
    """

    def __init__(
        self,
        orders: OrderRepository,
        executions: ExecutionRepository,
        risk_gate: RiskApprovalInterface,  # Doc 02: mandatory pre-trade gate
    ) -> None:
        self._orders = orders
        self._executions = executions
        self._risk_gate = risk_gate

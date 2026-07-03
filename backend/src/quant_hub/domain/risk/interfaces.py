# Governing specification: Doc 15 §11.5 — Risk Management Architecture
#                          Doc 07 — Backend Architecture §Layers §Dependency Rules
# Layer: Domain — Doc 07 §Layers
# Invariants: Port-3, Port-4, Port-5, P-1, P-2, P-5
# Per Doc 00 §14.11
from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from quant_hub.domain.risk.entities import (
    PreTradeRiskResult,
    RiskAssessment,
    RiskLimit,
    RiskMetrics,
)


class RiskModelInterface(ABC):
    """Risk computation contract — Doc 15 §11.5.4 Risk Models.

    Risk model methodology is external configuration per P-1. The platform
    governs the framework; concrete models (covariance-based, factor-based,
    historical simulation, Monte Carlo) plug in through this interface.
    Computation shall be deterministic per Port-3.
    """

    @abstractmethod
    async def compute_metrics(
        self, portfolio_id: UUID, positions: list[object]
    ) -> RiskMetrics: ...


class RiskLimitRepository(ABC):
    """Persistence contract for governed risk limits — Doc 15 §11.5.7.

    Limits are stored in the analytics schema per Doc 09 §Schemas.
    Portfolio-level limits supersede strategy-level limits per Port-5.
    """

    @abstractmethod
    async def get_active_limits(self, portfolio_id: UUID) -> list[RiskLimit]: ...

    @abstractmethod
    async def save_limit(self, limit: RiskLimit) -> None: ...


class RiskAssessmentRepository(ABC):
    """Persistence contract for risk assessment artifacts — Doc 15 §11.5.13.

    Assessments are immutable governed artifacts per P-2 and P-5 (audit trail).
    """

    @abstractmethod
    async def save(self, assessment: RiskAssessment) -> None: ...

    @abstractmethod
    async def get_latest(self, portfolio_id: UUID) -> RiskAssessment | None: ...


class PreTradeRiskRepository(ABC):
    """Persistence contract for pre-trade risk check records — Doc 14 §10.7.5.

    One record per gate evaluation of one proposed order (analytics.risk_assessments).
    Records are immutable audit artifacts per P-5 and §10.7.5 ("Rejection reason
    shall be recorded. Rejections shall not be silently swallowed"). Distinct
    from RiskAssessmentRepository above, which persists the §11.5.13
    portfolio-level RiskAssessment (a different artifact — see F-14).
    """

    @abstractmethod
    async def save(self, result: PreTradeRiskResult) -> None: ...

    @abstractmethod
    async def get_by_order(self, order_id: UUID) -> PreTradeRiskResult | None: ...


class RiskSnapshotRepository(ABC):
    """Persistence contract for analytics.risk_snapshots — Doc 07 §Implementation Rules.

    Retained for real-time dashboard queries (Doc 15 §11.5.8 risk monitoring dashboards).
    """

    @abstractmethod
    async def get_latest(self, portfolio_id: UUID) -> object | None: ...

    @abstractmethod
    async def save(self, snapshot: object) -> None: ...

# Governing specification: Doc 15 §11.5 — Risk Management Architecture
#                          Doc 07 — Backend Architecture §Layers §Dependency Rules
# Layer: Domain — Doc 07 §Layers
# Invariants: Port-3, Port-4, Port-5, P-1, P-2, P-5
# Per Doc 00 §14.11
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from decimal import Decimal
from uuid import UUID

from quant_hub.domain.risk.entities import (
    PreTradeRiskResult,
    RiskLimit,
    RiskLimitAssessment,
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
        self, portfolio_id: UUID, positions: list[object], equity: Decimal
    ) -> RiskMetrics:
        """Compute portfolio risk metrics — Doc 15 §11.5.3.

        `equity` is the capital base the leverage ratios are denominated
        against — supplied by the caller because the platform has no NAV/cash
        ledger yet (F-18), mirroring how the risk gate and sizing take
        portfolio_value as an input.
        """
        ...


class RiskLimitRepository(ABC):
    """Persistence contract for governed risk limits — Doc 15 §11.5.7.

    Limits are stored in the analytics schema per Doc 09 §Schemas.
    Portfolio-level limits supersede strategy-level limits per Port-5.
    """

    @abstractmethod
    async def get_active_limits(self, portfolio_id: UUID) -> list[RiskLimit]: ...

    @abstractmethod
    async def save_limit(self, limit: RiskLimit) -> None: ...


class PreTradeRiskRepository(ABC):
    """Persistence contract for pre-trade risk check records — Doc 14 §10.7.5.

    One record per gate evaluation of one proposed order (analytics.risk_assessments).
    Records are immutable audit artifacts per P-5 and §10.7.5 ("Rejection reason
    shall be recorded. Rejections shall not be silently swallowed"). Distinct
    from the §11.5.13 portfolio-level risk snapshot (RiskSnapshotRepository /
    analytics.risk_snapshots — a different artifact; see F-14, RESOLVED).
    """

    @abstractmethod
    async def save(self, result: PreTradeRiskResult) -> None: ...

    @abstractmethod
    async def get_by_order(self, order_id: UUID) -> PreTradeRiskResult | None: ...

    @abstractmethod
    async def list_by_portfolio(
        self, portfolio_id: UUID, limit: int
    ) -> list[PreTradeRiskResult]:
        """Most-recent-first pre-trade assessments for `portfolio_id`, up to `limit`.

        Added in Step 4.6 (the pre-trade assessment history — approved/rejected
        with reasons). A bounded recent window over the immutable §10.7.5 audit
        log, where get_by_order returns only the single record for one order.
        """
        ...


class RiskSnapshotRepository(ABC):
    """Persistence contract for analytics.risk_snapshots — Doc 07 §Implementation Rules.

    A snapshot is a persisted point-in-time RiskMetrics plus any limit breaches
    (Doc 15 §11.5.3 / §11.5.8). Immutable audit artifact per P-5. Retained for
    real-time dashboard queries (§11.5.8 risk monitoring dashboards).
    """

    @abstractmethod
    async def get_latest(self, portfolio_id: UUID) -> RiskMetrics | None: ...

    @abstractmethod
    async def get_latest_record(self, portfolio_id: UUID) -> dict | None:
        """Latest snapshot as its raw persisted row (or None) — Step 4.6.

        Unlike get_latest (which reconstructs a RiskMetrics for the risk
        service), this returns the row verbatim including the risk_metrics
        JSONB's own `deferred` list and the recorded breaches — the honest
        source of truth for the snapshot view, so DEFERRED metrics (F-18) are
        named as recorded rather than reconstructed or shown as real zeros.
        """
        ...

    @abstractmethod
    async def save(
        self, metrics: RiskMetrics, breaches: Sequence[RiskLimitAssessment]
    ) -> UUID: ...

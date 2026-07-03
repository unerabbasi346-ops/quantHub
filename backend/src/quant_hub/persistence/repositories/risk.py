# Governing specification: Doc 07 — Backend Architecture §Persistence Layer
#                          Doc 15 §11.5.7, §11.5.13 — Risk Limit Framework, Risk Artifacts
#                          Doc 09 — Database Schema (analytics schema)
# Layer: Persistence — Doc 07 §Layers
# Repository pattern — Doc 07 §Implementation Rules
# Per Doc 00 §14.11
from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy import text

from quant_hub.domain.risk.entities import (
    PreTradeCheck,
    PreTradeRiskResult,
    RiskAssessment,
    RiskLimit,
)
from quant_hub.domain.risk.interfaces import (
    PreTradeRiskRepository,
    RiskAssessmentRepository,
    RiskLimitRepository,
    RiskSnapshotRepository,
)
from quant_hub.persistence.repositories.base import BaseRepository


class SQLAlchemyRiskLimitRepository(BaseRepository[object], RiskLimitRepository):
    """Concrete repository for governed risk limits — Doc 15 §11.5.7.

    Maps to analytics.risk_limits (migration b2e4c9d17a30, Step 3.4). Raw-SQL
    via sqlalchemy.text(), same approach as every other repository; does not
    commit (caller owns the transaction boundary, Doc 07 §Implementation
    Rules). Portfolio-level limits supersede strategy limits per Port-5 — the
    persistence layer stores all limits; the service layer enforces precedence.
    """

    async def get_active_limits(self, portfolio_id: UUID) -> list[RiskLimit]:
        result = await self._session.execute(
            text(
                """
                SELECT id, portfolio_id, metric_name, limit_value, warning_threshold
                FROM analytics.risk_limits
                WHERE portfolio_id = :portfolio_id AND is_active
                ORDER BY metric_name, limit_value, id
                """
            ),
            {"portfolio_id": portfolio_id},
        )
        return [
            RiskLimit(
                limit_id=row["id"],
                portfolio_id=row["portfolio_id"],
                metric_name=row["metric_name"],
                limit_value=row["limit_value"],
                warning_threshold=row["warning_threshold"],
            )
            for row in result.mappings().all()
        ]

    async def save_limit(self, limit: RiskLimit) -> None:
        """Persist a governed limit (active). The entity's `limit_id` is used
        as the row id so save/get round-trip the same identity. Does not commit.
        """
        await self._session.execute(
            text(
                """
                INSERT INTO analytics.risk_limits
                    (id, portfolio_id, metric_name, limit_value, warning_threshold, is_active)
                VALUES
                    (:id, :portfolio_id, :metric_name, :limit_value, :warning_threshold, TRUE)
                """
            ),
            {
                "id": limit.limit_id,
                "portfolio_id": limit.portfolio_id,
                "metric_name": limit.metric_name,
                "limit_value": limit.limit_value,
                "warning_threshold": limit.warning_threshold,
            },
        )


class SQLAlchemyPreTradeRiskRepository(BaseRepository[object], PreTradeRiskRepository):
    """Concrete repository for pre-trade risk check records — Doc 14 §10.7.5.

    Maps to analytics.risk_assessments (migration b2e4c9d17a30, Step 3.4).
    Append-only immutable audit artifact per P-5 (§10.7.5: "Rejection reason
    shall be recorded. Rejections shall not be silently swallowed"). Does not
    commit. individual_checks is JSON-encoded and cast to ::jsonb, same pattern
    as SQLAlchemySignalRepository.record.
    """

    async def save(self, result: PreTradeRiskResult) -> None:
        checks = [
            {"check_name": c.check_name, "passed": c.passed, "detail": c.detail}
            for c in result.individual_checks
        ]
        await self._session.execute(
            text(
                """
                INSERT INTO analytics.risk_assessments
                    (id, order_id, portfolio_id, authorized, rejection_reason,
                     individual_checks, computation_latency_ns, assessed_at)
                VALUES
                    (:id, :order_id, :portfolio_id, :authorized, :rejection_reason,
                     CAST(:individual_checks AS JSONB), :computation_latency_ns, :assessed_at)
                """
            ),
            {
                "id": result.check_id,
                "order_id": result.order_id,
                "portfolio_id": result.portfolio_id,
                "authorized": result.authorized,
                "rejection_reason": result.rejection_reason,
                "individual_checks": json.dumps(checks),
                "computation_latency_ns": result.computation_latency_ns,
                "assessed_at": result.assessed_at,
            },
        )

    async def get_by_order(self, order_id: UUID) -> PreTradeRiskResult | None:
        result = await self._session.execute(
            text(
                """
                SELECT id, order_id, portfolio_id, authorized, rejection_reason,
                       individual_checks, computation_latency_ns, assessed_at
                FROM analytics.risk_assessments
                WHERE order_id = :order_id
                ORDER BY assessed_at DESC, id
                LIMIT 1
                """
            ),
            {"order_id": order_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            return None
        checks = tuple(
            PreTradeCheck(
                check_name=c["check_name"], passed=c["passed"], detail=c["detail"]
            )
            for c in (row["individual_checks"] or [])
        )
        return PreTradeRiskResult(
            check_id=row["id"],
            order_id=row["order_id"],
            portfolio_id=row["portfolio_id"],
            authorized=row["authorized"],
            rejection_reason=row["rejection_reason"],
            individual_checks=checks,
            computation_latency_ns=row["computation_latency_ns"],
            assessed_at=row["assessed_at"],
        )


class SQLAlchemyRiskAssessmentRepository(BaseRepository[object], RiskAssessmentRepository):
    """Concrete repository for risk assessment artifacts — Doc 15 §11.5.13.

    Assessments are immutable governed artifacts per P-2 and P-5.
    Maps to analytics schema per Doc 09.
    """

    async def save(self, assessment: RiskAssessment) -> None:
        pass  # stub

    async def get_latest(self, portfolio_id: UUID) -> RiskAssessment | None:
        return None  # stub


class SQLAlchemyRiskSnapshotRepository(BaseRepository[object], RiskSnapshotRepository):
    """Concrete repository for analytics.risk_snapshots — Doc 09 §Schemas.

    Retained for real-time risk dashboard queries per Doc 15 §11.5.8.
    """

    async def get_latest(self, portfolio_id: UUID) -> object | None:
        return None  # stub

    async def save(self, snapshot: object) -> None:
        pass  # stub

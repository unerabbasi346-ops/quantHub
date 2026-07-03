# Governing specification: Doc 07 — Backend Architecture §Persistence Layer
#                          Doc 15 §11.5.7, §11.5.13 — Risk Limit Framework, Risk Artifacts
#                          Doc 09 — Database Schema (analytics schema)
# Layer: Persistence — Doc 07 §Layers
# Repository pattern — Doc 07 §Implementation Rules
# Per Doc 00 §14.11
from __future__ import annotations

import json
from collections.abc import Sequence
from decimal import Decimal
from uuid import UUID

from sqlalchemy import text

from quant_hub.domain.risk.entities import (
    PreTradeCheck,
    PreTradeRiskResult,
    RiskAssessment,
    RiskLimit,
    RiskLimitAssessment,
    RiskMetrics,
)
from quant_hub.domain.risk.interfaces import (
    PreTradeRiskRepository,
    RiskAssessmentRepository,
    RiskLimitRepository,
    RiskSnapshotRepository,
)
from quant_hub.persistence.repositories.base import BaseRepository

# §11.5.3 metrics that Step 3.6 leaves at 0 pending return-series history (F-18).
_DEFERRED_METRICS = (
    "var_1d_99", "cvar_1d_99", "volatility_annualized", "max_drawdown", "beta",
)
# Every RiskMetrics numeric field, captured verbatim in the risk_metrics JSONB
# (the table's typed columns cover only a subset).
_METRIC_FIELDS = _DEFERRED_METRICS + (
    "gross_exposure", "net_exposure", "gross_leverage", "net_leverage",
)


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


def _metrics_to_json(metrics: RiskMetrics) -> dict:
    return {
        **{f: str(getattr(metrics, f)) for f in _METRIC_FIELDS},
        "deferred": list(_DEFERRED_METRICS),  # marks the F-18 zeros as not-yet-computed
    }


def _breaches_to_json(breaches: Sequence[RiskLimitAssessment]) -> list[dict]:
    return [
        {
            "metric_name": b.limit.metric_name,
            "current_value": str(b.current_value),
            "limit_value": str(b.limit.limit_value),
            "utilization": str(b.utilization),
            "status": b.status.value,
        }
        for b in breaches
    ]


class SQLAlchemyRiskSnapshotRepository(BaseRepository[object], RiskSnapshotRepository):
    """Concrete repository for analytics.risk_snapshots — Doc 15 §11.5.3/§11.5.8.

    Maps a RiskMetrics + limit breaches onto the Step 1.1 risk_snapshots table.
    The table has typed columns for a subset (var_1d_99, gross/net_exposure,
    leverage, drawdown_max); the FULL metric set is captured verbatim in the
    risk_metrics JSONB so nothing is lost. Append-only immutable snapshot per
    P-5. Does not commit (caller owns the transaction boundary).
    """

    async def save(
        self, metrics: RiskMetrics, breaches: Sequence[RiskLimitAssessment]
    ) -> UUID:
        stmt = text(
            """
            INSERT INTO analytics.risk_snapshots
                (portfolio_id, snapshot_at, var_1d_99, gross_exposure, net_exposure,
                 leverage, drawdown_max, risk_metrics, breaches)
            VALUES
                (:portfolio_id, :snapshot_at, :var_1d_99, :gross_exposure, :net_exposure,
                 :leverage, :drawdown_max, CAST(:risk_metrics AS JSONB), CAST(:breaches AS JSONB))
            RETURNING id
            """
        )
        result = await self._session.execute(
            stmt,
            {
                "portfolio_id": metrics.portfolio_id,
                "snapshot_at": metrics.computed_at,
                "var_1d_99": metrics.var_1d_99,
                "gross_exposure": metrics.gross_exposure,
                "net_exposure": metrics.net_exposure,
                "leverage": metrics.gross_leverage,
                "drawdown_max": metrics.max_drawdown,
                "risk_metrics": json.dumps(_metrics_to_json(metrics)),
                "breaches": json.dumps(_breaches_to_json(breaches)),
            },
        )
        return result.scalar_one()

    async def get_latest(self, portfolio_id: UUID) -> RiskMetrics | None:
        result = await self._session.execute(
            text(
                """
                SELECT portfolio_id, snapshot_at, risk_metrics
                FROM analytics.risk_snapshots
                WHERE portfolio_id = :portfolio_id
                ORDER BY snapshot_at DESC, id
                LIMIT 1
                """
            ),
            {"portfolio_id": portfolio_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            return None
        m = row["risk_metrics"] or {}
        return RiskMetrics(
            portfolio_id=row["portfolio_id"],
            computed_at=row["snapshot_at"],
            **{f: Decimal(m.get(f, "0")) for f in _METRIC_FIELDS},
        )

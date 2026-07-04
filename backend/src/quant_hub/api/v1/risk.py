# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
#   §API Standards: REST/FastAPI, versioned, Pydantic validation, OpenAPI.
# Doc 08 — Frontend Architecture (QH-008 v1.0) §API Layer: answers the risk
#   feature's snapshot/limits/assessment reads (features/risk).
# Doc 10 — API Specification (QH-010 v1.0): shared ResponseEnvelope.
# Doc 14 §10.7.5 — Pre-Trade Risk Check (the assessment audit records).
# Doc 15 §11.5.3 Risk Measurement, §11.5.7 Risk Limit Framework, §11.5.8
#   Continuous Monitoring — the limits/utilization/snapshot read shapes.
# Per Doc 00 §14.11
#
# Step 4.6, the Risk vertical slice: read endpoints over Phase 3.4's
# analytics.risk_limits / analytics.risk_assessments and Phase 3.6's
# analytics.risk_snapshots — all written by the real pre-trade gate and the
# real portfolio-risk snapshot path.
#
# JUDGMENT CALLS (Doc 00 §14.5/§14.7 — flagged):
#  1. snake_case JSON + Decimal-as-string, identical to Steps 4.2–4.5. Every
#     limit value / exposure / leverage / utilization is a STRING.
#  2. HONEST F-18 DEFERRED METRICS (the one to get right — same discipline as
#     Step 4.5's F-9). §11.5.3 lists VaR, CVaR, annualized volatility, max
#     drawdown, and beta, but Step 3.6 leaves them at 0 pending return-series /
#     equity-curve history the platform does not accumulate (F-18). The snapshot
#     response does NOT present those zeros as measurements: it returns the
#     COMPUTED metrics (gross/net exposure, gross/net leverage) as real values
#     and lists the DEFERRED metrics by name + reason in a separate
#     `deferred_metrics` array (read from the snapshot's own recorded `deferred`
#     marker), so the UI shows them as "not computed", never as a real 0.
#  3. HONEST UTILIZATION (same discipline). A limit's utilization is only shown
#     where it can actually be computed: continuous-monitoring limits
#     (gross/net leverage, var, ... — Doc 15 §11.5.8) are evaluated against the
#     latest snapshot by reusing RiskService.check_limits (the real monitoring
#     comparison, not a re-derivation). Pre-trade order-projection limits
#     (position_size, gross_exposure — evaluated per ORDER at §10.7.5, not
#     against a standing portfolio value) carry `evaluation="pre_trade"` and a
#     NULL utilization, rather than a fabricated portfolio-level number. The
#     per-order utilization for those lives in the assessment history instead.
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query, status
from pydantic import BaseModel, field_serializer

from quant_hub.api.dependencies import (
    PortfolioRepo,
    PreTradeRiskRepo,
    RiskLimitRepo,
    RiskServiceDep,
    RiskSnapshotRepo,
)
from quant_hub.api.envelope import ApiError, ErrorCode, ResponseEnvelope, ok
from quant_hub.domain.risk.entities import PreTradeRiskResult, RiskLimit
from quant_hub.domain.risk.pretrade import PRETRADE_METRICS

router = APIRouter(tags=["risk"])

# Why each §11.5.3 metric is deferred (F-18) — surfaced so the UI states the
# reason, not just the fact. Keys match the snapshot's recorded `deferred` list.
_DEFERRED_REASONS: dict[str, str] = {
    "var_1d_99": "Needs a portfolio return distribution (historical or parametric). Deferred per F-18.",
    "cvar_1d_99": "Needs a portfolio return distribution (tail beyond VaR). Deferred per F-18.",
    "volatility_annualized": "Needs a portfolio return series. Deferred per F-18.",
    "max_drawdown": "Needs an equity-curve / NAV history. Deferred per F-18.",
    "beta": "Needs asset + benchmark return histories. Deferred per F-18.",
}


# ── Risk limits ─────────────────────────────────────────────────────────────
class RiskLimitOut(BaseModel):
    """A governed risk limit (Doc 15 §11.5.7) with its current utilization.

    `evaluation` distinguishes continuous-monitoring limits (utilization
    computed against the latest snapshot) from pre-trade order-projection
    limits (evaluated per order at §10.7.5 — no standing portfolio utilization,
    so current_value/utilization/status are null here; see history endpoint)."""

    limit_id: UUID
    metric_name: str
    limit_value: Decimal
    warning_threshold: Decimal
    evaluation: str  # "continuous" | "pre_trade"
    current_value: Decimal | None
    utilization: Decimal | None
    status: str | None  # "ok" | "warning" | "breach", or null when not evaluated

    @field_serializer(
        "limit_value", "warning_threshold", "current_value", "utilization", when_used="json"
    )
    def _ser(self, v: Decimal | None) -> str | None:
        return None if v is None else format(v, "f")


# ── Pre-trade assessment history ────────────────────────────────────────────
class PreTradeCheckOut(BaseModel):
    check_name: str
    passed: bool
    detail: str


class PreTradeAssessmentOut(BaseModel):
    """One §10.7.5 pre-trade gate evaluation of one order — the audit record."""

    check_id: UUID
    order_id: UUID
    portfolio_id: UUID
    authorized: bool
    rejection_reason: str | None
    individual_checks: list[PreTradeCheckOut]
    computation_latency_ns: int
    assessed_at: datetime

    @classmethod
    def from_result(cls, r: PreTradeRiskResult) -> "PreTradeAssessmentOut":
        return cls(
            check_id=r.check_id,
            order_id=r.order_id,
            portfolio_id=r.portfolio_id,
            authorized=r.authorized,
            rejection_reason=r.rejection_reason,
            individual_checks=[
                PreTradeCheckOut(check_name=c.check_name, passed=c.passed, detail=c.detail)
                for c in r.individual_checks
            ],
            computation_latency_ns=r.computation_latency_ns,
            assessed_at=r.assessed_at,
        )


# ── Portfolio risk snapshot ─────────────────────────────────────────────────
class DeferredMetricOut(BaseModel):
    """A §11.5.3 metric that is NOT computed yet (F-18) — named, with the
    reason, so the UI shows it as deferred rather than as a real zero."""

    name: str
    reason: str


class RiskBreachOut(BaseModel):
    metric_name: str
    current_value: str
    limit_value: str
    utilization: str
    status: str


class RiskSnapshotOut(BaseModel):
    """Latest portfolio risk snapshot — Doc 15 §11.5.3.

    Exposure/leverage are REAL computed values (Step 3.6, PositionExposureRisk
    Model). VaR/CVaR/volatility/drawdown/beta are DEFERRED (F-18) and appear
    ONLY in `deferred_metrics` (by name + reason), never as fabricated zeros."""

    portfolio_id: UUID
    snapshot_at: datetime
    gross_exposure: Decimal
    net_exposure: Decimal
    gross_leverage: Decimal
    net_leverage: Decimal
    deferred_metrics: list[DeferredMetricOut]
    breaches: list[RiskBreachOut]

    @field_serializer(
        "gross_exposure", "net_exposure", "gross_leverage", "net_leverage", when_used="json"
    )
    def _ser(self, v: Decimal) -> str:
        return format(v, "f")


async def _require_portfolio(portfolio_repo: PortfolioRepo, portfolio_id: UUID) -> None:
    if await portfolio_repo.get_by_id(portfolio_id) is None:
        raise ApiError(
            status.HTTP_404_NOT_FOUND,
            ErrorCode.RESOURCE_NOT_FOUND,
            f"Portfolio {portfolio_id} not found",
        )


def _limit_out(limit: RiskLimit, assessment: Any | None) -> RiskLimitOut:
    evaluation = "pre_trade" if limit.metric_name in PRETRADE_METRICS else "continuous"
    if assessment is not None:
        return RiskLimitOut(
            limit_id=limit.limit_id,
            metric_name=limit.metric_name,
            limit_value=limit.limit_value,
            warning_threshold=limit.warning_threshold,
            evaluation=evaluation,
            current_value=assessment.current_value,
            utilization=assessment.utilization,
            status=assessment.status.value,
        )
    return RiskLimitOut(
        limit_id=limit.limit_id,
        metric_name=limit.metric_name,
        limit_value=limit.limit_value,
        warning_threshold=limit.warning_threshold,
        evaluation=evaluation,
        current_value=None,
        utilization=None,
        status=None,
    )


@router.get(
    "/portfolios/{portfolio_id}/risk/limits",
    response_model=ResponseEnvelope[list[RiskLimitOut]],
    summary="Governed risk limits and their current utilization",
)
async def get_risk_limits(
    portfolio_id: UUID,
    portfolio_repo: PortfolioRepo,
    limit_repo: RiskLimitRepo,
    snapshot_repo: RiskSnapshotRepo,
    risk_service: RiskServiceDep,
) -> ResponseEnvelope[list[RiskLimitOut]]:
    await _require_portfolio(portfolio_repo, portfolio_id)
    limits = await limit_repo.get_active_limits(portfolio_id)
    # Utilization for CONTINUOUS-monitoring limits, computed against the latest
    # snapshot by the real §11.5.8 comparison (RiskService.check_limits). Absent
    # a snapshot, or for pre-trade limits, utilization is null (judgment call #3).
    by_limit_id: dict[UUID, Any] = {}
    metrics = await snapshot_repo.get_latest(portfolio_id)
    if metrics is not None:
        for a in await risk_service.check_limits(portfolio_id, metrics):
            by_limit_id[a.limit.limit_id] = a
    return ok([_limit_out(lim, by_limit_id.get(lim.limit_id)) for lim in limits])


@router.get(
    "/portfolios/{portfolio_id}/risk/assessments",
    response_model=ResponseEnvelope[list[PreTradeAssessmentOut]],
    summary="Pre-trade risk assessment history (approved/rejected + reasons)",
)
async def get_risk_assessments(
    portfolio_id: UUID,
    portfolio_repo: PortfolioRepo,
    pretrade_repo: PreTradeRiskRepo,
    limit: int = Query(100, ge=1, le=1000, description="Max most-recent assessments"),
) -> ResponseEnvelope[list[PreTradeAssessmentOut]]:
    await _require_portfolio(portfolio_repo, portfolio_id)
    assessments = await pretrade_repo.list_by_portfolio(portfolio_id, limit)
    return ok([PreTradeAssessmentOut.from_result(a) for a in assessments])


@router.get(
    "/portfolios/{portfolio_id}/risk/snapshot",
    response_model=ResponseEnvelope[RiskSnapshotOut | None],
    summary="Latest portfolio risk snapshot (exposure/leverage; deferred metrics named)",
)
async def get_risk_snapshot(
    portfolio_id: UUID,
    portfolio_repo: PortfolioRepo,
    snapshot_repo: RiskSnapshotRepo,
) -> ResponseEnvelope[RiskSnapshotOut | None]:
    await _require_portfolio(portfolio_repo, portfolio_id)
    record = await snapshot_repo.get_latest_record(portfolio_id)
    if record is None:
        # Portfolio exists but no snapshot has been computed — a legitimate
        # state (null), distinct from "no such portfolio" (404 above).
        return ok(None)
    metrics: dict[str, Any] = record["risk_metrics"] or {}
    deferred_names = metrics.get("deferred", [])
    deferred = [
        DeferredMetricOut(name=n, reason=_DEFERRED_REASONS.get(n, "Deferred — F-18"))
        for n in deferred_names
    ]
    breaches = [
        RiskBreachOut(
            metric_name=b["metric_name"],
            current_value=b["current_value"],
            limit_value=b["limit_value"],
            utilization=b["utilization"],
            status=b["status"],
        )
        for b in (record["breaches"] or [])
    ]
    return ok(
        RiskSnapshotOut(
            portfolio_id=record["portfolio_id"],
            snapshot_at=record["snapshot_at"],
            gross_exposure=Decimal(metrics.get("gross_exposure", "0")),
            net_exposure=Decimal(metrics.get("net_exposure", "0")),
            gross_leverage=Decimal(metrics.get("gross_leverage", "0")),
            net_leverage=Decimal(metrics.get("net_leverage", "0")),
            deferred_metrics=deferred,
            breaches=breaches,
        )
    )

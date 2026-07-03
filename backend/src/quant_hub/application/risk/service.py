# Governing specification: Doc 15 §11.5 — Risk Management Architecture
#                          Doc 02 — System Architecture §Dependency Rules (Risk Engine approves every order)
#                          Doc 07 — Backend Architecture §Application Layer
# Layer: Application — Doc 07 §Layers
# Invariants: Port-3, Port-4, Port-5, P-1, P-2, P-5
# Per Doc 00 §14.11
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from quant_hub.domain.risk.entities import (
    PreTradeCheck,
    PreTradeRiskRequest,
    PreTradeRiskResult,
    RiskAssessment,
    RiskLimitAssessment,
    RiskLimitStatus,
    RiskMetrics,
)
from quant_hub.domain.risk.interfaces import (
    PreTradeRiskRepository,
    RiskAssessmentRepository,
    RiskLimitRepository,
    RiskModelInterface,
    RiskSnapshotRepository,
)
from quant_hub.domain.risk.pretrade import evaluate_pretrade

logger = logging.getLogger(__name__)

# Metric_name -> RiskMetrics attribute for §11.5.8 continuous-monitoring
# limit checks (check_limits). Pre-trade order-projection metrics
# (position_size, gross_exposure) are handled separately by evaluate_pretrade.
_METRIC_ATTRS: dict[str, str] = {
    "var_1d_99": "var_1d_99",
    "cvar_1d_99": "cvar_1d_99",
    "volatility_annualized": "volatility_annualized",
    "max_drawdown": "max_drawdown",
    "beta": "beta",
    "gross_leverage": "gross_leverage",
    "net_leverage": "net_leverage",
}


class RiskService:
    """Risk management application service — Doc 15 §11.5 / Doc 07 §Application Layer.

    Responsibilities per Doc 15 §11.5:
    - Pre-trade order assessment (satisfies Doc 02 mandatory risk gate)
    - Portfolio risk metric computation per Port-3 (Deterministic Portfolio State)
    - Continuous limit monitoring per Port-4 (Continuous Risk Monitoring)
    - Portfolio-level limit authority per Port-5 (Strategy Risk Separation)

    Step 3.4: pre-trade order gating (assess_pre_trade) and §11.5.8
    continuous-monitoring limit checks (check_limits) are real. Portfolio
    metric COMPUTATION (compute_portfolio_metrics) still delegates to the
    configured RiskModelInterface, which remains the StubRiskModel until a
    real covariance/factor model is configured (Step 3.6) — P-1: the model is
    external config, orthogonal to the limit-enforcement framework built here.
    """

    def __init__(
        self,
        risk_model: RiskModelInterface,           # P-1: model is external config
        limits: RiskLimitRepository,
        assessments: RiskAssessmentRepository,
        snapshots: RiskSnapshotRepository,
        pretrade: PreTradeRiskRepository,
    ) -> None:
        self._model = risk_model
        self._limits = limits
        self._assessments = assessments
        self._snapshots = snapshots
        self._pretrade = pretrade

    async def assess_pre_trade(self, request: PreTradeRiskRequest) -> PreTradeRiskResult:
        """Pre-trade risk assessment — Doc 14 §10.7.5 / Doc 02 mandatory gate.

        Loads the portfolio's active governed limits (Doc 15 §11.5.7) and
        evaluates whether the proposed order would breach a position-size or
        exposure limit AFTER execution (§10.7.5). Portfolio-level limits are
        authoritative per Port-5. Produces the §10.7.5 record (authorized,
        rejection_reason, individual_checks, check_id, computation_latency_ns)
        and persists it immutably to analytics.risk_assessments for audit
        (§10.7.5: "Rejection reason shall be recorded. Rejections shall not be
        silently swallowed"). Does not commit — caller owns the transaction.

        FAIL-CLOSED per §10.7.5 timeout behavior / T-6 (default-deny; "no
        silent allow"): if the limit load or evaluation raises, the order is
        DENIED (authorized=False), never approved. This is the behavioral half
        of the fail-safe posture — the DI half (production binds the real gate,
        never the always-approve StubRiskApprovalService) lives in
        api/dependencies.provide_risk_gate.
        """
        start = time.perf_counter_ns()
        check_id = uuid4()
        assessed_at = datetime.now(timezone.utc)

        try:
            limits = await self._limits.get_active_limits(request.portfolio_id)
            authorized, reason, checks, _assessments = evaluate_pretrade(request, limits)
        except Exception as exc:  # noqa: BLE001 — fail-closed is the whole point
            authorized = False
            reason = f"risk check failed to complete: {type(exc).__name__}"
            checks = (PreTradeCheck(check_name="risk_limits", passed=False, detail=reason),)
            logger.error(
                "pre-trade risk check failed to complete; failing closed "
                "(order_id=%s portfolio_id=%s): %s",
                request.order_id, request.portfolio_id, exc,
            )

        latency_ns = time.perf_counter_ns() - start
        result = PreTradeRiskResult(
            check_id=check_id,
            order_id=request.order_id,
            portfolio_id=request.portfolio_id,
            authorized=authorized,
            rejection_reason=reason,
            individual_checks=checks,
            computation_latency_ns=latency_ns,
            assessed_at=assessed_at,
        )
        if not authorized:
            logger.warning(
                "pre-trade risk REJECTED order_id=%s portfolio_id=%s: %s",
                request.order_id, request.portfolio_id, reason,
            )
        # Audit record (§10.7.5). Persistence failure propagates to the caller's
        # transaction — an unrecorded check must not let the order proceed.
        await self._pretrade.save(result)
        return result

    async def compute_portfolio_metrics(
        self, portfolio_id: UUID, positions: list[object], equity: Decimal
    ) -> RiskMetrics:
        """Compute portfolio risk metrics — Doc 15 §11.5.3.

        Delegates to the configured RiskModelInterface per P-1 (model is config).
        Deterministic per Port-3: same inputs produce same outputs. With the
        real PositionExposureRiskModel (Step 3.6) this returns real exposure/
        leverage; VaR/CVaR/volatility/drawdown/beta remain 0 pending return
        history (F-18).
        """
        return await self._model.compute_metrics(portfolio_id, positions, equity)

    async def snapshot_portfolio_risk(
        self, portfolio_id: UUID, positions: list[object], equity: Decimal
    ) -> RiskMetrics:
        """Compute + persist a portfolio risk snapshot — Doc 15 §11.5.3/§11.5.8.

        Computes current metrics, evaluates them against active governed limits
        (§11.5.8 monitoring — breaches recorded), and persists both to
        analytics.risk_snapshots as an immutable point-in-time artifact (P-5).
        Does not commit — caller owns the transaction. Returns the metrics.
        """
        metrics = await self._model.compute_metrics(portfolio_id, positions, equity)
        assessments = await self.check_limits(portfolio_id, metrics)
        breaches = tuple(a for a in assessments if a.status is RiskLimitStatus.BREACH)
        await self._snapshots.save(metrics, breaches)
        return metrics

    async def check_limits(
        self, portfolio_id: UUID, metrics: RiskMetrics
    ) -> list[RiskLimitAssessment]:
        """Check portfolio metrics against governed limits — Doc 15 §11.5.7/11.5.8.

        The §11.5.8 continuous-monitoring path (distinct from the §10.7.5
        pre-trade path above): compares a current RiskMetrics snapshot against
        each active portfolio-level limit whose metric_name names a metric
        field (var_1d_99, gross_leverage, max_drawdown, ...). Warning at the
        warning_threshold, breach at the limit (§11.5.8). Breaches trigger
        immediate escalation per Port-4 (escalation wiring itself is Step 3.6).

        Pre-trade order-projection metrics (position_size, gross_exposure) are
        NOT evaluated here — they have no meaning against a portfolio snapshot;
        they belong to assess_pre_trade. Returns one assessment per matched
        limit, in the limits' natural load order.
        """
        limits = await self._limits.get_active_limits(portfolio_id)
        assessments: list[RiskLimitAssessment] = []
        for lim in limits:
            attr = _METRIC_ATTRS.get(lim.metric_name)
            if attr is None:
                continue  # not a portfolio-metric limit (e.g. a pre-trade limit)
            value = getattr(metrics, attr)
            if value > lim.limit_value:
                status = RiskLimitStatus.BREACH
            elif value >= lim.warning_threshold:
                status = RiskLimitStatus.WARNING
            else:
                status = RiskLimitStatus.OK
            utilization = value / lim.limit_value if lim.limit_value != 0 else value
            assessments.append(
                RiskLimitAssessment(
                    limit=lim,
                    current_value=value,
                    utilization=utilization,
                    status=status,
                )
            )
        return assessments

    async def get_latest_assessment(self, portfolio_id: UUID) -> RiskAssessment | None:
        """Retrieve latest risk assessment artifact — Doc 15 §11.5.13.

        Assessments are immutable governed artifacts per P-2 and P-5.
        """
        return await self._assessments.get_latest(portfolio_id)

# Governing specification: Doc 14 §10.7.5 — Order Validation (Risk Limit Checks)
#                          Doc 14 §Pre-Trade Risk Check API Contract
#                          Doc 15 §11.5.7 — Risk Limit Framework
# Layer: Domain — Doc 07 §Layers (pure computation; no persistence, no I/O)
# Invariants: Port-3 (Deterministic Portfolio State), Port-4, Port-5, P-13 (determinism)
# Scope: handbook/KNOWN_LIMITATIONS.md S-5 / F-15 (pre-trade check subset)
# Per Doc 00 §14.11
#
# Step 3.4: the pure pass/fail core of the pre-trade risk gate. Given a
# proposed order (PreTradeRiskRequest) and the portfolio's active governed
# limits, it decides authorize/reject and produces the §10.7.5 individual
# check results. Deterministic per Port-3/P-13: identical (request, limits)
# always yield identical (authorized, reason, checks). check_id, latency, and
# persistence are the SERVICE's concern (application/risk/service.py), kept
# out of here so the decision itself stays pure and reproducible.
from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from quant_hub.domain.risk.entities import (
    PreTradeCheck,
    PreTradeRiskRequest,
    RiskLimit,
    RiskLimitAssessment,
    RiskLimitStatus,
)

# The metric_names this pre-trade gate evaluates (S-5, F-15). Other limit
# metrics (var_1d_99, gross_leverage, max_drawdown, ...) are portfolio-level
# CONTINUOUS-monitoring limits (Doc 15 §11.5.8) checked against a RiskMetrics
# snapshot by RiskService.check_limits — NOT order-projection limits. A limit
# whose metric_name is outside this set is ignored by the pre-trade gate (it
# is not a "this order would breach ... after execution" check per §10.7.5).
PRETRADE_METRICS: frozenset[str] = frozenset({"position_size", "gross_exposure"})

_ZERO = Decimal("0")


def _projected_metric_value(metric_name: str, request: PreTradeRiskRequest) -> Decimal | None:
    """Projected post-execution value for a pre-trade metric — §10.7.5
    "Order would not breach ... after execution".

    position_size  — absolute position quantity (units) after this order fills.
    gross_exposure — absolute post-execution notional as a fraction of
                     portfolio value (a leverage/concentration measure,
                     Doc 15 §11.5.7). Returns None if it cannot be computed
                     (portfolio_value <= 0), which the caller treats as a
                     failed check (fail-closed — we cannot prove compliance).
    """
    if metric_name == "position_size":
        return abs(request.projected_quantity)
    if metric_name == "gross_exposure":
        if request.portfolio_value <= _ZERO:
            return None
        return abs(request.projected_quantity * request.price) / request.portfolio_value
    return None  # not reachable: caller filters to PRETRADE_METRICS


def _status(current_value: Decimal, limit: RiskLimit) -> RiskLimitStatus:
    if current_value > limit.limit_value:
        return RiskLimitStatus.BREACH
    if current_value >= limit.warning_threshold:
        return RiskLimitStatus.WARNING
    return RiskLimitStatus.OK


def evaluate_pretrade(
    request: PreTradeRiskRequest,
    limits: Sequence[RiskLimit],
) -> tuple[bool, str | None, tuple[PreTradeCheck, ...], tuple[RiskLimitAssessment, ...]]:
    """Evaluate a proposed order against active governed limits — §10.7.5.

    Returns (authorized, rejection_reason, individual_checks, limit_assessments).

    All applicable checks are evaluated (not short-circuited) so every result
    is recorded for audit per §10.7.5 ("All check results SHALL be recorded ...
    regardless of fail-fast behavior"); `rejection_reason` reports the FIRST
    breach in deterministic order. authorized == (no BREACH among evaluated
    checks). A limit that cannot be evaluated (e.g. gross_exposure with a
    non-positive portfolio value) fails closed — passed=False — rather than
    being silently skipped.

    Deterministic per Port-3/P-13: limits are evaluated in a stable order
    (metric_name, limit_value, limit_id), independent of input ordering or of
    how many active limits share a metric_name (F-14: no natural-key
    uniqueness on analytics.risk_limits, so duplicates are handled here).
    """
    applicable = sorted(
        (lim for lim in limits if lim.metric_name in PRETRADE_METRICS),
        key=lambda lim: (lim.metric_name, lim.limit_value, str(lim.limit_id)),
    )

    if not applicable:
        # No order-projection limits configured — nothing this order breaches.
        # Recorded explicitly (not an empty check list) so the audit trail is
        # unambiguous about WHY the order was authorized.
        check = PreTradeCheck(
            check_name="risk_limits",
            passed=True,
            detail="no active pre-trade limits configured for portfolio; no limit breached",
        )
        return True, None, (check,), ()

    checks: list[PreTradeCheck] = []
    assessments: list[RiskLimitAssessment] = []
    rejection_reason: str | None = None

    for lim in applicable:
        value = _projected_metric_value(lim.metric_name, request)
        check_name = f"risk_limit:{lim.metric_name}"

        if value is None:
            detail = (
                f"{lim.metric_name}: cannot evaluate (portfolio_value="
                f"{request.portfolio_value}); failing closed"
            )
            checks.append(PreTradeCheck(check_name=check_name, passed=False, detail=detail))
            if rejection_reason is None:
                rejection_reason = detail
            continue

        status = _status(value, lim)
        utilization = value / lim.limit_value if lim.limit_value != _ZERO else _ZERO
        assessments.append(
            RiskLimitAssessment(
                limit=lim,
                current_value=value,
                utilization=utilization,
                status=status,
            )
        )
        passed = status is not RiskLimitStatus.BREACH
        detail = (
            f"{lim.metric_name}: projected={value} vs limit={lim.limit_value} "
            f"(warn={lim.warning_threshold}, util={utilization:.4f}) -> {status.value}"
        )
        checks.append(PreTradeCheck(check_name=check_name, passed=passed, detail=detail))
        if not passed and rejection_reason is None:
            rejection_reason = (
                f"{lim.metric_name} limit breached: projected {value} exceeds "
                f"limit {lim.limit_value}"
            )

    authorized = rejection_reason is None
    return authorized, rejection_reason, tuple(checks), tuple(assessments)

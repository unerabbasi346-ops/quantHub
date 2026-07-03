# Governing specification: Doc 14 §10.7.5 — Order Validation / Pre-Trade Risk Check
#                          Doc 15 §11.5.7–§11.5.8 — Risk Limit Framework / Monitoring
#                          Doc 02 — Risk Engine mandatory pre-trade gate
# Per Doc 00 §14.11
#
# Pure-computation + fake-repo tests for Step 3.4 (real Pre-Trade Risk). The
# real analytics.risk_limits / analytics.risk_assessments writes are exercised
# in the live verification, not here. Covers: the deterministic evaluator, the
# service's fail-closed posture, check_limits, and the fail-safe DI (production
# gate is the real adapter, never the always-approve stub).
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from quant_hub.api.dependencies import build_risk_gate
from quant_hub.application.risk.service import RiskService
from quant_hub.domain.execution.entities import OrderSide
from quant_hub.domain.risk.entities import (
    PreTradeRiskRequest,
    RiskLimit,
    RiskLimitStatus,
    RiskMetrics,
)
from quant_hub.domain.risk.pretrade import PRETRADE_METRICS, evaluate_pretrade
from quant_hub.infrastructure.risk_approval import StubRiskApprovalService
from quant_hub.infrastructure.risk_approval_adapter import RiskApprovalAdapter
from quant_hub.infrastructure.risk_model_stub import StubRiskModel

_PORTFOLIO = uuid4()


def _limit(metric: str, value: str, warn: str | None = None) -> RiskLimit:
    limit_value = Decimal(value)
    return RiskLimit(
        limit_id=uuid4(),
        portfolio_id=_PORTFOLIO,
        metric_name=metric,
        limit_value=limit_value,
        warning_threshold=Decimal(warn) if warn is not None else limit_value * Decimal("0.8"),
    )


def _request(
    *,
    side: OrderSide = OrderSide.BUY,
    quantity: str = "1",
    price: str = "100",
    current: str = "0",
    portfolio_value: str = "100000",
) -> PreTradeRiskRequest:
    return PreTradeRiskRequest(
        order_id=uuid4(),
        portfolio_id=_PORTFOLIO,
        strategy_id=uuid4(),
        asset_id=uuid4(),
        side=side,
        quantity=Decimal(quantity),
        price=Decimal(price),
        current_quantity=Decimal(current),
        portfolio_value=Decimal(portfolio_value),
        timestamp=datetime.now(timezone.utc),
    )


# ── Projection arithmetic (§10.7.5 "after execution") ───────────────────────

def test_projected_quantity_buy_adds_to_current() -> None:
    req = _request(side=OrderSide.BUY, quantity="3", current="2")
    assert req.signed_delta == Decimal("3")
    assert req.projected_quantity == Decimal("5")


def test_projected_quantity_sell_reduces_current() -> None:
    req = _request(side=OrderSide.SELL, quantity="3", current="5")
    assert req.signed_delta == Decimal("-3")
    assert req.projected_quantity == Decimal("2")


# ── Evaluator: no limits configured ─────────────────────────────────────────

def test_no_limits_authorizes_with_explicit_check() -> None:
    authorized, reason, checks, assessments = evaluate_pretrade(_request(), [])
    assert authorized is True
    assert reason is None
    assert len(checks) == 1
    assert checks[0].check_name == "risk_limits" and checks[0].passed is True
    assert assessments == ()


# ── Evaluator: position-size limit ──────────────────────────────────────────

def test_position_size_within_limit_authorized() -> None:
    # projected position = 5 units, limit = 10 → OK
    req = _request(quantity="5", current="0")
    authorized, reason, checks, assessments = evaluate_pretrade(req, [_limit("position_size", "10")])
    assert authorized is True
    assert reason is None
    assert assessments[0].status is RiskLimitStatus.OK


def test_position_size_breach_rejects() -> None:
    # projected position = 15 units, limit = 10 → BREACH
    req = _request(quantity="15", current="0")
    authorized, reason, checks, assessments = evaluate_pretrade(req, [_limit("position_size", "10")])
    assert authorized is False
    assert reason is not None and "position_size" in reason
    assert assessments[0].status is RiskLimitStatus.BREACH
    assert any(not c.passed for c in checks)


def test_position_size_breach_counts_existing_position() -> None:
    # already hold 8, buy 5 → projected 13 > limit 10 → BREACH
    req = _request(quantity="5", current="8")
    authorized, _, _, _ = evaluate_pretrade(req, [_limit("position_size", "10")])
    assert authorized is False


def test_position_size_at_exactly_limit_is_ok() -> None:
    # projected == limit is NOT a breach (breach is strictly greater)
    req = _request(quantity="10", current="0")
    authorized, _, _, assessments = evaluate_pretrade(req, [_limit("position_size", "10", warn="20")])
    assert authorized is True
    assert assessments[0].status is RiskLimitStatus.OK


def test_position_size_warning_still_authorized() -> None:
    # projected 9, warn 8, limit 10 → WARNING but authorized
    req = _request(quantity="9", current="0")
    authorized, reason, _, assessments = evaluate_pretrade(
        req, [_limit("position_size", "10", warn="8")]
    )
    assert authorized is True
    assert reason is None
    assert assessments[0].status is RiskLimitStatus.WARNING


# ── Evaluator: gross-exposure limit ─────────────────────────────────────────

def test_gross_exposure_within_limit_authorized() -> None:
    # notional = 5 * 100 = 500; pv = 100000 → exposure 0.005; limit 0.30 → OK
    req = _request(quantity="5", price="100", portfolio_value="100000")
    authorized, _, _, assessments = evaluate_pretrade(req, [_limit("gross_exposure", "0.30")])
    assert authorized is True
    assert assessments[0].status is RiskLimitStatus.OK


def test_gross_exposure_breach_rejects() -> None:
    # notional = 500 * 100 = 50000; pv = 100000 → exposure 0.50; limit 0.30 → BREACH
    req = _request(quantity="500", price="100", portfolio_value="100000")
    authorized, reason, _, assessments = evaluate_pretrade(req, [_limit("gross_exposure", "0.30")])
    assert authorized is False
    assert "gross_exposure" in (reason or "")
    assert assessments[0].status is RiskLimitStatus.BREACH


def test_gross_exposure_zero_portfolio_value_fails_closed() -> None:
    req = _request(quantity="1", price="100", portfolio_value="0")
    authorized, reason, checks, _ = evaluate_pretrade(req, [_limit("gross_exposure", "0.30")])
    assert authorized is False
    assert "cannot evaluate" in (reason or "")
    assert any(not c.passed for c in checks)


# ── Evaluator: determinism / multiple + irrelevant limits ───────────────────

def test_non_pretrade_metric_is_ignored() -> None:
    # a portfolio-monitoring limit (var_1d_99) must not affect the pre-trade gate
    req = _request(quantity="5", current="0")
    limits = [_limit("var_1d_99", "0.01"), _limit("position_size", "10")]
    authorized, _, checks, assessments = evaluate_pretrade(req, limits)
    assert authorized is True
    assert all("var_1d_99" not in c.check_name for c in checks)
    assert all(a.limit.metric_name in PRETRADE_METRICS for a in assessments)


def test_evaluation_is_order_independent() -> None:
    req = _request(quantity="15", current="0")
    a = [_limit("position_size", "20"), _limit("position_size", "10")]  # tighter is 10
    r1 = evaluate_pretrade(req, a)
    r2 = evaluate_pretrade(req, list(reversed(a)))
    # same authorized decision + same rejection reason regardless of input order
    assert r1[0] == r2[0] == False  # noqa: E712 — explicit False for clarity
    assert r1[1] == r2[1]


# ── RiskService: fail-closed + persistence ──────────────────────────────────


class _FakeLimitRepo:
    def __init__(self, limits: list[RiskLimit], *, raises: bool = False) -> None:
        self._limits = limits
        self._raises = raises

    async def get_active_limits(self, portfolio_id: UUID) -> list[RiskLimit]:
        if self._raises:
            raise RuntimeError("simulated limit-store outage")
        return list(self._limits)

    async def save_limit(self, limit: RiskLimit) -> None:  # pragma: no cover
        pass


class _FakePreTradeRepo:
    def __init__(self) -> None:
        self.saved: list = []

    async def save(self, result) -> None:
        self.saved.append(result)

    async def get_by_order(self, order_id: UUID):  # pragma: no cover
        return self.saved[-1] if self.saved else None


def _service(limits: list[RiskLimit], *, raises: bool = False):
    pretrade = _FakePreTradeRepo()
    svc = RiskService(
        risk_model=StubRiskModel(),
        limits=_FakeLimitRepo(limits, raises=raises),
        snapshots=None,
        pretrade=pretrade,
    )
    return svc, pretrade


@pytest.mark.asyncio
async def test_assess_pre_trade_authorizes_and_persists() -> None:
    svc, pretrade = _service([_limit("position_size", "10")])
    result = await svc.assess_pre_trade(_request(quantity="5"))
    assert result.authorized is True
    assert result.rejection_reason is None
    assert result.check_id is not None
    assert result.computation_latency_ns >= 0
    assert len(pretrade.saved) == 1 and pretrade.saved[0] is result


@pytest.mark.asyncio
async def test_assess_pre_trade_rejects_and_persists_reason() -> None:
    svc, pretrade = _service([_limit("position_size", "10")])
    result = await svc.assess_pre_trade(_request(quantity="15"))
    assert result.authorized is False
    assert result.rejection_reason and "position_size" in result.rejection_reason
    assert pretrade.saved[0].authorized is False


@pytest.mark.asyncio
async def test_assess_pre_trade_fails_closed_on_repo_error() -> None:
    # The core fail-safe behavior: an internal failure DENIES, never approves,
    # and the denial is still recorded (§10.7.5 default-deny / T-6).
    svc, pretrade = _service([], raises=True)
    result = await svc.assess_pre_trade(_request(quantity="1"))
    assert result.authorized is False
    assert "failed to complete" in (result.rejection_reason or "")
    assert len(pretrade.saved) == 1 and pretrade.saved[0].authorized is False


# ── RiskService.check_limits (§11.5.8 monitoring path) ───────────────────────

def _metrics(**over) -> RiskMetrics:
    base = dict(
        portfolio_id=_PORTFOLIO,
        var_1d_99=Decimal("0"),
        cvar_1d_99=Decimal("0"),
        volatility_annualized=Decimal("0"),
        max_drawdown=Decimal("0"),
        beta=Decimal("0"),
        gross_exposure=Decimal("0"),
        net_exposure=Decimal("0"),
        gross_leverage=Decimal("0"),
        net_leverage=Decimal("0"),
        computed_at=datetime.now(timezone.utc),
    )
    base.update(over)
    return RiskMetrics(**base)


@pytest.mark.asyncio
async def test_check_limits_detects_metric_breach_and_ignores_pretrade_metric() -> None:
    svc, _ = _service([_limit("gross_leverage", "2.0"), _limit("position_size", "10")])
    assessments = await svc.check_limits(_PORTFOLIO, _metrics(gross_leverage=Decimal("3.0")))
    # only the portfolio-metric limit is assessed; position_size is skipped
    assert len(assessments) == 1
    assert assessments[0].limit.metric_name == "gross_leverage"
    assert assessments[0].status is RiskLimitStatus.BREACH


# ── Fail-safe DI: production gate is the REAL adapter, never the stub ────────

def test_build_risk_gate_returns_real_adapter_not_stub() -> None:
    gate = build_risk_gate(session=object())  # repos only store the session
    assert isinstance(gate, RiskApprovalAdapter)
    assert not isinstance(gate, StubRiskApprovalService)


@pytest.mark.asyncio
async def test_adapter_denies_wrong_input_type_fail_closed() -> None:
    # Feeding the gate something that is not a PreTradeRiskRequest must DENY,
    # not approve — the stub's unconditional approval is never the fallback.
    class _NullService:
        async def assess_pre_trade(self, request):  # pragma: no cover
            raise AssertionError("should not be reached for wrong input type")

    adapter = RiskApprovalAdapter(_NullService())
    decision = await adapter.evaluate(object())
    assert decision.approved is False
    assert "unassessable" in decision.reason


@pytest.mark.asyncio
async def test_adapter_maps_authorized_result_to_approved() -> None:
    svc, _ = _service([_limit("position_size", "10")])
    adapter = RiskApprovalAdapter(svc)
    decision = await adapter.evaluate(_request(quantity="5"))
    assert decision.approved is True
    assert "check_id" in decision.reason

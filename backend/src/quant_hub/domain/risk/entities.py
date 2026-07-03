# Governing specification: Doc 15 §11.5 — Risk Management Architecture
# Layer: Domain — Doc 07 §Layers
# Invariants: Port-3 (Deterministic Portfolio State), Port-4 (Continuous Risk Monitoring),
#             Port-5 (Strategy Risk Separation), P-2 (Immutability), P-5 (Audit Trail)
# Per Doc 00 §14.11
from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from quant_hub.domain.execution.entities import OrderSide


@dataclass(frozen=True)
class RiskMetrics:
    """Portfolio-level risk metrics snapshot — Doc 15 §11.5.3 Risk Measurement.

    Deterministic per Port-3: identical positions, market data, and risk model
    parameters shall produce identical metrics.
    Immutable after creation per P-2.
    """

    portfolio_id: UUID
    # VaR / CVaR — Doc 15 §11.5.3
    var_1d_99: Decimal           # Value at Risk, 1-day horizon, 99% confidence
    cvar_1d_99: Decimal          # Conditional VaR (Expected Shortfall) — tail risk
    # Volatility — Doc 15 §11.5.3
    volatility_annualized: Decimal
    # Drawdown — Doc 15 §11.5.3
    max_drawdown: Decimal        # Peak-to-trough decline
    # Exposure — Doc 15 §11.5.3
    beta: Decimal                # Market beta to primary benchmark
    gross_leverage: Decimal      # Gross leverage
    net_leverage: Decimal        # Net leverage
    # Anchors determinism per Port-3
    computed_at: datetime


class RiskLimitStatus(enum.Enum):
    """Risk limit utilization status — Doc 15 §11.5.8.

    Warning triggered at warning_threshold (≥80% of limit by convention).
    Breach triggers immediate escalation per Port-4.
    """

    OK = "ok"
    WARNING = "warning"  # >= warning_threshold, < limit_value
    BREACH = "breach"    # >= limit_value — Port-4: immediate escalation required


@dataclass(frozen=True)
class RiskLimit:
    """A single governed portfolio-level risk limit — Doc 15 §11.5.7.

    Portfolio-level limits supersede strategy-level limits per Port-5.
    Limits are governed assets: set by risk governance, monitored continuously per Port-4.

    `portfolio_id` (added Step 3.4, F-14): a limit is portfolio-scoped per
    §11.5.7 ("Portfolio-level risk limits"). The Step 0.6 skeleton omitted it
    because the read path (RiskLimitRepository.get_active_limits(portfolio_id))
    carried the scope externally; it is embedded here so a RiskLimit is a
    complete, persistable/loadable governed asset (save_limit needs to know
    which portfolio it belongs to) and round-trips through analytics.risk_limits
    without losing its owner.
    """

    limit_id: UUID
    portfolio_id: UUID
    metric_name: str             # e.g. "position_size", "gross_exposure", "var_1d_99"
    limit_value: Decimal         # Breach threshold
    warning_threshold: Decimal   # Warning threshold (typically 0.80 × limit_value)


@dataclass(frozen=True)
class RiskLimitAssessment:
    """Assessment of one limit against current metric value — Doc 15 §11.5.8."""

    limit: RiskLimit
    current_value: Decimal
    utilization: Decimal         # current_value / limit.limit_value
    status: RiskLimitStatus


@dataclass(frozen=True)
class RiskAssessment:
    """Complete point-in-time risk assessment for one portfolio — Doc 15 §11.5.

    Immutable after creation per P-2.
    Recorded as a governed artifact per Doc 15 §11.5.13 and P-5 (audit trail).
    """

    assessment_id: UUID
    portfolio_id: UUID
    metrics: RiskMetrics
    limit_assessments: tuple[RiskLimitAssessment, ...]
    breaches: tuple[RiskLimitAssessment, ...]  # subset where status == BREACH
    assessed_at: datetime


# ---------------------------------------------------------------------------
# Pre-Trade Risk Check — Doc 14 §10.7.5 / §Pre-Trade Risk Check API Contract
# ---------------------------------------------------------------------------
# Distinct from the §11.5.13 portfolio-level RiskAssessment above: these value
# objects model the ORDER-level gate that authorizes or rejects a single
# proposed order before routing (Doc 14 §10.7.4 CREATED -> VALIDATED/REJECTED).
# Scoped per S-5 to risk-limit checks (position-size, exposure) only — the
# other §10.7.5 checks (compliance, price sanity, trading schedule, instrument
# state, duplicate detection, quantity/lot) are deferred (F-15).


@dataclass(frozen=True)
class PreTradeRiskRequest:
    """One proposed order to be gated — Doc 14 §10.7.5 request contract.

    Carries the §10.7.5 request fields (order_id, strategy_id, instrument,
    side, quantity, price, order_type via the originating order, timestamp)
    PLUS the projection context §10.7.5 requires to evaluate limits "after
    execution": the signed current position and the portfolio value the
    exposure fraction is denominated against.

    Assembled by the CALLER (F-15): a RecordedOrder (Step 3.3) alone does not
    carry price / current position / portfolio value, so the caller gathers
    them (price = the reference the order was priced at; current_quantity from
    core.positions; portfolio_value from portfolio state). Automatic
    context-gathering inside a live ExecutionService is not built this step
    (ExecutionService is still the Step 0.4 stub).

    Immutable per P-2. `quantity` is the ABSOLUTE order size (> 0); direction
    is carried by `side`.
    """

    order_id: UUID
    portfolio_id: UUID
    strategy_id: UUID | None
    asset_id: UUID
    side: OrderSide
    quantity: Decimal            # absolute order size in units, > 0
    price: Decimal               # reference price for notional (> 0)
    current_quantity: Decimal    # signed current holding (0 = flat)
    portfolio_value: Decimal     # AUM the exposure fraction is denominated against
    timestamp: datetime

    @property
    def signed_delta(self) -> Decimal:
        """Signed position change this order applies (+ for BUY, − for SELL)."""
        return self.quantity if self.side is OrderSide.BUY else -self.quantity

    @property
    def projected_quantity(self) -> Decimal:
        """Signed position after this order executes — §10.7.5 "after execution"."""
        return self.current_quantity + self.signed_delta


@dataclass(frozen=True)
class PreTradeCheck:
    """One individual check result — Doc 14 §Pre-Trade Risk Check API Contract
    ("individual_checks": list[{check_name, passed, detail}]).

    Recorded for audit whether or not it passed (§10.7.5: "All check results
    SHALL be recorded in the audit trail regardless of fail-fast behavior").
    """

    check_name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class PreTradeRiskResult:
    """Outcome of a pre-trade risk check — Doc 14 §Pre-Trade Risk Check API
    Contract response shape.

    The pass/fail DECISION (authorized, individual_checks, rejection_reason) is
    a pure deterministic function of (request, active limits) per Port-3/P-13.
    `check_id` and `computation_latency_ns` are non-deterministic audit metadata
    assigned by the service, not inputs to the decision. Persisted immutably to
    analytics.risk_assessments per P-5 / §10.7.5 ("Rejection reason shall be
    recorded. Rejections shall not be silently swallowed").
    """

    check_id: UUID
    order_id: UUID
    portfolio_id: UUID
    authorized: bool
    rejection_reason: str | None
    individual_checks: tuple[PreTradeCheck, ...]
    computation_latency_ns: int
    assessed_at: datetime

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
    """

    limit_id: UUID
    metric_name: str             # e.g. "var_1d_99", "gross_leverage", "max_drawdown"
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

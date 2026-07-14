# Governing specification: Doc 14 §10.3.7 — Performance Metrics. F-21.
# Layer: Domain — Doc 07 §Layers (value objects; no persistence, no I/O)
# Invariants: P-2 (immutability)
# Per Doc 00 §14.11
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class EquityPoint:
    """One real, mark-to-market equity observation from a backtest replay —
    analytics.backtest_equity_curve (migration c7d3f9a2e5b8). `step` 0 is the
    baseline (config.initial_capital, before any bar is processed); step N is
    the mark-to-market value after processing the Nth historical bar.
    `return_pct` is this step's fractional return vs the PRIOR step (0 for
    the step-0 baseline).
    """

    step: int
    ts: object  # datetime; typed loosely per this module's convention
    portfolio_value: Decimal
    return_pct: Decimal


@dataclass(frozen=True)
class ComputedMetrics:
    """The Doc 14 §10.3.7 metric suite for one completed backtest run —
    analytics.backtest_computed_metrics. Every field is `None` when it
    genuinely could not be computed (e.g. zero decided trades for win_rate)
    — never a fabricated 0 standing in for "unknown". `None` here is
    forwarded as JSON `null` by the API layer (Doc 00 §14.5/§14.7).
    """

    backtest_run_id: UUID
    win_rate: Decimal | None
    sharpe_ratio: Decimal | None
    sortino_ratio: Decimal | None
    max_drawdown_pct: Decimal | None
    calmar_ratio: Decimal | None
    profit_factor: Decimal | None
    expectancy_per_trade: Decimal | None

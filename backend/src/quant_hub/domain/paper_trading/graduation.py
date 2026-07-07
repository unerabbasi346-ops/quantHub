# Governing specification: Doc 05 — Engineering Standards (mandatory paper
#   trading before any live promotion; the .docx per V-2). Doc 14 §10.5.9
#   (Paper-to-Live Promotion Gate) — the promotion-gate requirements this check
#   records evidence against; §10.5.10 (Paper Trading Artifacts, the session
#   `results` this reads); §10.5.8 (the paper-vs-backtest comparison figure).
# Layer: Domain — Doc 07 §Layers (a PURE evaluator: no I/O, no DB, no clock —
#   deterministic given its inputs, so it is fully unit-testable).
# Invariants: P-2 (promotion evidence recorded), P-13 (deterministic).
# Scope: handbook/KNOWN_LIMITATIONS.md S-8 (graduation criteria included now vs
#   deferred), F-18 (the risk-metric criteria that stay deferred).
# Per Doc 00 §14.11
#
# Step 5.4 — the Graduation Criteria Record. Doc 05 makes paper trading a
# MANDATORY gate before live; Doc 14 §10.5.9 enumerates the promotion-gate
# requirements. This module answers a deliberately narrow question: has a paper
# session cleared the MINIMUM bar to even be ELIGIBLE for a human to consider it
# for live promotion? It is a record/checklist, NOT an automated approver —
# nothing here greenlights live trading. A human authorises promotion (Doc 05);
# this produces the honestly-reasoned pass/fail evidence they read.
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

# Criteria that a REAL §10.5.9 gate would also require but that are DEFERRED
# because the metrics behind them are not computed yet (F-18: VaR/CVaR,
# Sharpe/Sortino, annualized volatility, max drawdown all need a portfolio
# return-series / equity curve this platform does not accumulate). Recorded on
# every record so the checklist is honest about what it does NOT yet check —
# never silently omitted. See S-8.
DEFERRED_CRITERIA: tuple[str, ...] = (
    "var_cvar_within_limit (F-18 — no VaR/CVaR computed)",
    "sharpe_sortino_above_floor (F-18 — no return series)",
    "max_drawdown_within_limit (F-18 — no equity curve)",
    "multi_regime_minimum_duration (§10.5.9 — needs a real multi-condition span)",
    "risk_control_and_circuit_breaker_validation (§10.5.9 — no live-limit exercise yet)",
)


@dataclass(frozen=True)
class GraduationThresholds:
    """The minimum-bar thresholds. Every value is a JUDGMENT CALL (Doc 00
    §14.5/§14.7) — a proportionate FLOOR for this platform's current stage, not
    a statistically-validated promotion standard. Callers may override.

    - `min_bars` (20): the session must have driven at least this many live
      bars. §10.5.9 asks for a duration "spanning multiple market conditions"; a
      real minimum would be far larger (weeks of bars). 20 is an honest floor
      proving the runner sustained real live processing, explicitly NOT a
      multi-regime-duration claim (that stays deferred, see DEFERRED_CRITERIA).
    - `min_fills` (1): at least one REAL fill must have gone through the live
      pipeline (§10.5.9 "Infrastructure Validation — order management validated
      under live market conditions"). A floor of 1 proves the fill path actually
      executed live rather than the session no-op'ing; a real gate would want
      many fills across conditions.
    - `max_total_return_deviation` (0.05): |paper - backtest total return| must
      be within 5 percentage points (§10.5.9 "Performance Validation ... within
      acceptable deviation from backtest expectations", §10.5.8). 0.05 is an
      arbitrary-but-stated placeholder; a real tolerance would derive from the
      strategy's expected return variance / backtest confidence interval — which
      needs the return-series statistics F-18 defers.
    """

    min_bars: int = 20
    min_fills: int = 1
    max_total_return_deviation: Decimal = Decimal("0.05")


@dataclass(frozen=True)
class CriterionResult:
    """One checklist line: did this specific criterion pass, and why."""

    id: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class GraduationRecord:
    """The full pass/fail record. `overall_pass` is the AND of every criterion —
    but it is EVIDENCE, not an authorisation: a human still decides promotion
    (Doc 05). `deferred_criteria` names the §10.5.9 checks not yet evaluated
    (F-18), so a reader is never misled that a pass means "fully validated"."""

    overall_pass: bool
    criteria: tuple[CriterionResult, ...]
    thresholds: GraduationThresholds
    deferred_criteria: tuple[str, ...] = DEFERRED_CRITERIA


def _to_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def evaluate_graduation(
    *,
    status: str,
    bars_processed: int,
    orders_filled: int,
    comparison: Mapping[str, object] | None,
    thresholds: GraduationThresholds | None = None,
) -> GraduationRecord:
    """Evaluate a paper session's final artifacts (Step 5.3 §10.5.10) against the
    minimum graduation bar. Pure: same inputs -> same record (P-13). Inputs are
    read straight from the session record + its `results` JSONB — no metric is
    recomputed here.
    """
    t = thresholds or GraduationThresholds()
    criteria: list[CriterionResult] = []

    # (1) Clean completion / no unhandled runner error. A crash never reaches the
    # runner's finalize, so the session would still be RUNNING — reaching STOPPED
    # IS the "the run completed without an unhandled error" signal (§10.5.9
    # Operational Validation). GRADUATED also counts (already promoted-eligible).
    clean = status in ("STOPPED", "GRADUATED")
    criteria.append(
        CriterionResult(
            "clean_completion",
            clean,
            f"status={status} (expected STOPPED — an unhandled runner error would leave it RUNNING)",
        )
    )

    # (2) Minimum live bars driven (§10.5.9 minimum duration — floor, not a
    # multi-regime claim).
    criteria.append(
        CriterionResult(
            "min_bars_processed",
            bars_processed >= t.min_bars,
            f"bars_processed={bars_processed} vs required minimum {t.min_bars}",
        )
    )

    # (3) At least one REAL fill through the live pipeline (§10.5.9 infrastructure
    # validation).
    criteria.append(
        CriterionResult(
            "min_real_fills",
            orders_filled >= t.min_fills,
            f"orders_filled={orders_filled} vs required minimum {t.min_fills}",
        )
    )

    # (4) Paper vs backtest within tolerance (§10.5.9 performance validation /
    # §10.5.8). Requires a linked backtest baseline; without one the criterion
    # fails honestly rather than being skipped.
    deviation = _to_decimal(comparison.get("total_return_deviation")) if comparison else None
    if deviation is None:
        criteria.append(
            CriterionResult(
                "comparison_within_tolerance",
                False,
                "no linked backtest / comparison unavailable (§10.5.8 baseline required for promotion)",
            )
        )
    else:
        criteria.append(
            CriterionResult(
                "comparison_within_tolerance",
                abs(deviation) <= t.max_total_return_deviation,
                f"|total_return_deviation|={abs(deviation)} vs tolerance {t.max_total_return_deviation}",
            )
        )

    overall = all(c.passed for c in criteria)
    return GraduationRecord(overall_pass=overall, criteria=tuple(criteria), thresholds=t)

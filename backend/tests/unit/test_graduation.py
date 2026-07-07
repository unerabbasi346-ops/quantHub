# Governing specification: Doc 05 (mandatory paper trading before live);
#   Doc 14 §10.5.9 (Promotion Gate), §10.5.8 (comparison). S-8; F-18.
# Per Doc 00 §14.11
#
# Step 5.4 — the PURE graduation evaluator. Deterministic over its inputs
# (no DB, no clock), so these pin the exact pass/fail logic and reasons.
from __future__ import annotations

from decimal import Decimal

from quant_hub.domain.paper_trading.graduation import (
    DEFERRED_CRITERIA,
    GraduationThresholds,
    evaluate_graduation,
)


def _passing(**overrides):
    kw = dict(
        status="STOPPED",
        bars_processed=25,
        orders_filled=3,
        comparison={"total_return_deviation": "0.01"},
    )
    kw.update(overrides)
    return evaluate_graduation(**kw)


def _by_id(record):
    return {c.id: c for c in record.criteria}


def test_all_criteria_pass() -> None:
    record = _passing()
    assert record.overall_pass is True
    assert all(c.passed for c in record.criteria)
    # the deferred (F-18) criteria are always surfaced, never silently dropped
    assert record.deferred_criteria == DEFERRED_CRITERIA


def test_running_status_fails_clean_completion() -> None:
    record = _passing(status="RUNNING")
    assert record.overall_pass is False
    assert _by_id(record)["clean_completion"].passed is False


def test_graduated_status_counts_as_clean() -> None:
    assert _by_id(_passing(status="GRADUATED"))["clean_completion"].passed is True


def test_too_few_bars_fails() -> None:
    record = _passing(bars_processed=2)  # default min_bars=20
    assert record.overall_pass is False
    c = _by_id(record)["min_bars_processed"]
    assert c.passed is False and "bars_processed=2" in c.detail


def test_no_fills_fails() -> None:
    record = _passing(orders_filled=0)
    assert _by_id(record)["min_real_fills"].passed is False


def test_deviation_outside_tolerance_fails() -> None:
    record = _passing(comparison={"total_return_deviation": "0.20"})  # > 0.05
    assert _by_id(record)["comparison_within_tolerance"].passed is False


def test_negative_deviation_uses_absolute_value() -> None:
    # a -0.20 deviation is just as far out of tolerance as +0.20
    record = _passing(comparison={"total_return_deviation": "-0.20"})
    assert _by_id(record)["comparison_within_tolerance"].passed is False
    assert _passing(comparison={"total_return_deviation": "-0.01"}).overall_pass is True


def test_missing_comparison_fails_honestly() -> None:
    record = _passing(comparison=None)
    c = _by_id(record)["comparison_within_tolerance"]
    assert c.passed is False and "no linked backtest" in c.detail


def test_comparison_without_deviation_key_fails() -> None:
    assert _by_id(_passing(comparison={}))["comparison_within_tolerance"].passed is False


def test_custom_thresholds_can_pass_a_short_session() -> None:
    # the real Step 5.3 verify session shape: 2 bars, 2 fills, tiny deviation
    lenient = GraduationThresholds(min_bars=2, min_fills=1, max_total_return_deviation=Decimal("0.05"))
    record = evaluate_graduation(
        status="STOPPED", bars_processed=2, orders_filled=2,
        comparison={"total_return_deviation": "0.000617513"}, thresholds=lenient,
    )
    assert record.overall_pass is True


def test_default_thresholds_fail_that_same_short_session() -> None:
    # honest: under the default 20-bar floor the 2-bar demo session does NOT graduate
    record = evaluate_graduation(
        status="STOPPED", bars_processed=2, orders_filled=2,
        comparison={"total_return_deviation": "0.000617513"},
    )
    assert record.overall_pass is False
    assert _by_id(record)["min_bars_processed"].passed is False
    # ...but every other criterion passes — the only blocker is duration
    assert _by_id(record)["clean_completion"].passed is True
    assert _by_id(record)["min_real_fills"].passed is True
    assert _by_id(record)["comparison_within_tolerance"].passed is True


# ── GraduationService (application seam) with a fake repository ──────────────

import pytest  # noqa: E402
from uuid import uuid4  # noqa: E402

from quant_hub.application.paper_trading.graduation_service import GraduationService  # noqa: E402


class _FakeSessions:
    def __init__(self, row: dict | None) -> None:
        self._row = row
        self.updated_results: dict | None = None
        self.update_kwargs: dict | None = None

    async def get_by_id(self, session_id):
        return self._row

    async def update_runtime(self, session_id, **kwargs):
        self.update_kwargs = kwargs
        self.updated_results = kwargs.get("results")


@pytest.mark.asyncio
async def test_service_appends_graduation_without_clobbering_existing_results() -> None:
    row = {
        "status": "STOPPED",
        "results": {
            "bars_processed": 2, "orders_filled": 2,
            "comparison": {"total_return_deviation": "0.000617513"},
            "realized_pnl": "50.0461",  # a pre-existing artifact key that must survive
        },
    }
    sessions = _FakeSessions(row)
    record = await GraduationService(sessions, now=lambda: _fixed()).evaluate(uuid4())

    assert record.overall_pass is False  # 2 < default 20 bars
    # existing artifact keys preserved; graduation appended
    assert sessions.updated_results["realized_pnl"] == "50.0461"
    grad = sessions.updated_results["graduation"]
    assert grad["overall_pass"] is False
    assert grad["evaluated_at"] == "2026-07-06T00:00:00+00:00"
    assert {c["id"] for c in grad["criteria"]} == {
        "clean_completion", "min_bars_processed", "min_real_fills", "comparison_within_tolerance"
    }
    # the service records evidence only — it does NOT set status (a human decides)
    assert "status" not in (sessions.update_kwargs or {})


@pytest.mark.asyncio
async def test_service_raises_on_missing_session() -> None:
    with pytest.raises(ValueError):
        await GraduationService(_FakeSessions(None)).evaluate(uuid4())


def _fixed():
    from datetime import datetime, timezone
    return datetime(2026, 7, 6, tzinfo=timezone.utc)

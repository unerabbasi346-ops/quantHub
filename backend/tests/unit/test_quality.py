# Governing specification: Doc 11 §6 — Data Quality Scoring (Data Engineering)
# Per Doc 00 §14.11
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from quant_hub.domain.market_data.quality import (
    QUALITY_CLEAN,
    QUALITY_STALE,
    assess_bar_quality,
    assess_tick_quality,
)


def test_bar_quality_passes_through_source_quality() -> None:
    assert assess_bar_quality(source_quality="CLEAN") == "CLEAN"


def test_bar_quality_does_not_invent_a_different_value() -> None:
    # Whatever the connector asserted is preserved — no freshness penalty
    # is applied to historical bars (see quality.py docstring).
    assert assess_bar_quality(source_quality="SOME_CUSTOM_FLAG") == "SOME_CUSTOM_FLAG"


def test_tick_quality_clean_when_fresh() -> None:
    now = datetime.now(timezone.utc)
    result = assess_tick_quality(ts=now, received_at=now, source_quality=QUALITY_CLEAN)
    assert result == QUALITY_CLEAN


def test_tick_quality_stale_when_old() -> None:
    now = datetime.now(timezone.utc)
    old_ts = now - timedelta(minutes=30)
    result = assess_tick_quality(ts=old_ts, received_at=now, source_quality=QUALITY_CLEAN)
    assert result == QUALITY_STALE


def test_tick_quality_within_tolerance_stays_clean() -> None:
    now = datetime.now(timezone.utc)
    almost_stale_ts = now - timedelta(minutes=2)
    result = assess_tick_quality(ts=almost_stale_ts, received_at=now, source_quality=QUALITY_CLEAN)
    assert result == QUALITY_CLEAN


def test_tick_quality_preserves_connector_asserted_flag_even_if_stale() -> None:
    now = datetime.now(timezone.utc)
    old_ts = now - timedelta(hours=1)
    result = assess_tick_quality(ts=old_ts, received_at=now, source_quality="ESTIMATED")
    assert result == "ESTIMATED"  # provenance flag not overwritten by staleness check


def test_tick_quality_handles_naive_datetimes() -> None:
    now_naive = datetime.now()
    result = assess_tick_quality(ts=now_naive, received_at=now_naive, source_quality=QUALITY_CLEAN)
    assert result == QUALITY_CLEAN

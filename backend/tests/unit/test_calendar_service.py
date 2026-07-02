# Governing specification: Doc 11 §4 — Timezone & Calendar Services (Data Engineering)
# Per Doc 00 §14.11
#
# No database needed (unlike tests/integration/) — pure logic on
# SystemCalendarService (infrastructure/market_data/calendar_service.py).
from __future__ import annotations

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from quant_hub.infrastructure.market_data.calendar_service import SystemCalendarService


def test_to_utc_passes_through_aware_timestamp() -> None:
    svc = SystemCalendarService()
    aware = datetime(2026, 7, 2, 13, 30, tzinfo=ZoneInfo("America/New_York"))

    result = svc.to_utc(aware, exchange="yfinance")

    assert result == datetime(2026, 7, 2, 17, 30, tzinfo=timezone.utc)


def test_to_utc_localizes_naive_timestamp_for_known_exchange() -> None:
    svc = SystemCalendarService()
    # 9:30 AM naive — NYSE open. July = EDT (UTC-4), so this must become
    # 13:30 UTC, NOT 09:30 UTC (the pre-Step-1.5 bug: naive was wrongly
    # treated as already-UTC).
    naive = datetime(2026, 7, 2, 9, 30)

    result = svc.to_utc(naive, exchange="yfinance")

    assert result == datetime(2026, 7, 2, 13, 30, tzinfo=timezone.utc)


def test_to_utc_naive_timestamp_dst_transition_handled_correctly() -> None:
    svc = SystemCalendarService()
    # January = EST (UTC-5), not EDT (UTC-4) — proves DST is handled via
    # zoneinfo's IANA data, not a hardcoded offset.
    naive_winter = datetime(2026, 1, 15, 9, 30)

    result = svc.to_utc(naive_winter, exchange="yfinance")

    assert result == datetime(2026, 1, 15, 14, 30, tzinfo=timezone.utc)


def test_to_utc_unknown_exchange_falls_back_to_utc() -> None:
    svc = SystemCalendarService()
    naive = datetime(2026, 7, 2, 9, 30)

    result = svc.to_utc(naive, exchange="some_unmapped_exchange")

    assert result == datetime(2026, 7, 2, 9, 30, tzinfo=timezone.utc)


def test_to_utc_unknown_exchange_logs_warning(caplog) -> None:
    svc = SystemCalendarService()
    naive = datetime(2026, 7, 2, 9, 30)

    with caplog.at_level("WARNING"):
        svc.to_utc(naive, exchange="some_unmapped_exchange")

    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == "WARNING"
    assert "some_unmapped_exchange" in caplog.records[0].getMessage()


def test_to_utc_known_exchange_does_not_log_warning(caplog) -> None:
    svc = SystemCalendarService()
    naive = datetime(2026, 7, 2, 9, 30)

    with caplog.at_level("WARNING"):
        svc.to_utc(naive, exchange="yfinance")

    assert len(caplog.records) == 0


def test_is_trading_day_crypto_always_true_including_weekends() -> None:
    svc = SystemCalendarService()
    saturday = date(2026, 7, 4)
    assert saturday.weekday() == 5

    assert svc.is_trading_day("crypto", "binance", saturday) is True


def test_is_trading_day_equity_false_on_weekend_true_on_weekday() -> None:
    svc = SystemCalendarService()
    saturday = date(2026, 7, 4)
    thursday = date(2026, 7, 2)

    assert svc.is_trading_day("equity", "yfinance", saturday) is False
    assert svc.is_trading_day("equity", "yfinance", thursday) is True


def test_is_trading_day_equity_has_no_holiday_awareness_documented_gap() -> None:
    svc = SystemCalendarService()
    # 2026-01-01 is a Thursday and a US market holiday (New Year's Day).
    # This asserts the DOCUMENTED gap: today's implementation returns True
    # (weekday-only check) even though real markets are closed. If this
    # assertion ever starts failing, holiday awareness has been added and
    # this test (and the calendar_service.py gap docstring) should be
    # updated together.
    new_years_day_2026 = date(2026, 1, 1)
    assert new_years_day_2026.weekday() < 5

    assert svc.is_trading_day("equity", "yfinance", new_years_day_2026) is True

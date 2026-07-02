# Governing specification: Doc 11 §4 — Timezone & Calendar Services (Data Engineering)
# Layer: Domain — Doc 07 §Layers
# Dependency rule: domain defines the interface; infrastructure implements it
#   — Doc 07 §Dependency Rules
# Per Doc 00 §14.11
#
# SCOPE (Step 1.5, per recorded scope decision handbook/KNOWN_LIMITATIONS.md
# S-1/S-2): implements Doc 11 §4's UTC-normalization and weekday-trading-day
# responsibilities. Holiday/half-day tracking is explicitly NOT implemented
# — see infrastructure/market_data/calendar_service.py for the flagged gap
# and rationale (nothing in the current pipeline gates behavior on
# trading-day/holiday status, so a full holiday calendar would be
# speculative ahead of an actual consumer).
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime


class TimezoneCalendarService(ABC):
    """UTC normalization + basic trading-day contract — Doc 11 §4.

    Doc 11 §4 Responsibilities: "Normalize timestamps to UTC internally",
    "Maintain exchange-local calendars", "Track holidays, half-days and
    daylight-saving transitions". Doc 11 §4 Acceptance: "Consumers receive
    deterministic timestamps regardless of source."
    """

    @abstractmethod
    def to_utc(self, dt: datetime, exchange: str) -> datetime:
        """Normalize a timestamp to UTC — Doc 11 §4.

        If `dt` is already timezone-aware, converts it directly. If `dt`
        is naive, it is interpreted as exchange-local time (per `exchange`)
        before converting — Doc 11 §4 "exchange-local calendars".
        """
        ...

    @abstractmethod
    def is_trading_day(self, asset_class: str, exchange: str, on: date) -> bool:
        """Whether `on` is a trading day for this asset class/exchange — Doc 11 §4.

        GAP (flagged, not silently omitted): weekday/weekend only today —
        no holiday or half-day awareness. See
        infrastructure/market_data/calendar_service.py's class docstring.
        """
        ...

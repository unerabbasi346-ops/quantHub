# Governing specification: Doc 11 §4 — Timezone & Calendar Services (Data Engineering)
# Layer: Infrastructure — Doc 07 §Layers
# Dependency rule: infrastructure implements domain interfaces — Doc 07 §Dependency Rules
# Per Doc 00 §14.11
from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from quant_hub.domain.market_data.calendar import TimezoneCalendarService

logger = logging.getLogger(__name__)

# JUDGMENT CALL (Doc 00 §14.5/§14.7 — flagged, not silently decided): Doc 11
# §4 requires "exchange-local calendars" but names neither which exchanges
# are in scope nor an exchange -> IANA timezone mapping. This table covers
# only what Steps 1.2/1.4 actually integrate. Crypto connectors (ccxt) never
# hit this path — they already return real UTC epoch timestamps (Step 1.2),
# so naive-timestamp interpretation is only relevant to yfinance-sourced
# equities today. yfinance's AssetRef.exchange is currently the literal
# string "yfinance" (the data source), not a real venue identifier — Step
# 1.2 already flagged symbol/venue normalization as unspecified by Doc 11 —
# so every yfinance-sourced equity is mapped to one default timezone
# (America/New_York, the dominant US market) rather than resolved per
# symbol/venue. Extend this table (and resolve real per-symbol venues, e.g.
# via yfinance's Ticker.info "exchange" field) if/when non-US equities are
# ingested.
_EXCHANGE_TIMEZONES: dict[str, ZoneInfo] = {
    "yfinance": ZoneInfo("America/New_York"),
}
_FALLBACK_TZ = ZoneInfo("UTC")


class SystemCalendarService(TimezoneCalendarService):
    """zoneinfo-based (Python stdlib) implementation of Doc 11 §4.

    GAP (flagged, per handbook/KNOWN_LIMITATIONS.md S-2 scope decision, not
    silently omitted): holiday and half-day tracking (Doc 11 §4: "Track
    holidays, half-days and daylight-saving transitions") is NOT
    implemented beyond weekday/weekend. DST transitions ARE handled
    correctly — that falls directly out of using the IANA tz database via
    zoneinfo for the astimezone() conversion, not separate logic. A real
    holiday calendar needs either a maintained third-party library (e.g.
    pandas_market_calendars — not currently a project dependency; Doc 11
    does not name one) or a hand-maintained table requiring annual upkeep.
    Deferred per the recorded solo-developer scope decision: nothing in
    the current pipeline gates ingestion or any other behavior on
    trading-day/holiday status, so building this now would be speculative
    ahead of an actual consumer.
    """

    def to_utc(self, dt: datetime, exchange: str) -> datetime:
        if dt.tzinfo is not None:
            return dt.astimezone(timezone.utc)
        if exchange not in _EXCHANGE_TIMEZONES:
            # Doc 00 §14.11 / observability: falling back to UTC for an
            # unmapped exchange is a silent mislabeling risk (a naive
            # timestamp from a real non-UTC venue would be misinterpreted
            # as UTC) — log it so a future misconfigured/new connector
            # leaves a trace instead of failing silently.
            logger.warning(
                "SystemCalendarService.to_utc: no timezone mapping for "
                "exchange=%r, falling back to UTC — naive timestamp may be "
                "mislabeled if this exchange is not actually UTC-native",
                exchange,
            )
        local_tz = _EXCHANGE_TIMEZONES.get(exchange, _FALLBACK_TZ)
        return dt.replace(tzinfo=local_tz).astimezone(timezone.utc)

    def is_trading_day(self, asset_class: str, exchange: str, on: date) -> bool:
        if asset_class == "crypto":
            return True  # 24/7 markets — Doc 11 §4 has no crypto-specific carve-out
        return on.weekday() < 5  # Mon-Fri; see class docstring for the holiday gap

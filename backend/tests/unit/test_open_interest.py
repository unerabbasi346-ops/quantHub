# Governing specification: Doc 11 §1/§2 (Market Data Connectors / Ingestion);
#   Doc 14 §10.9.5 (Financing Costs anchor); migration b4f8e21ac9d3.
# Per Doc 00 §14.11
#
# Unit-level coverage (no DB): (1) the domain entities carry the expected
# defaults/types; (2) CCXTConnector.fetch_open_interest_history's raw-row
# mapping — Decimal conversion, openInterestValue/openInterestAmount field
# mapping, and the skip-on-missing-data rule (Doc 11 §2: never fabricate a
# missing timestamp/notional) — exercised against a minimal fake ccxt
# exchange object (duck-typed; no real network I/O). Idempotency and the
# real read/write path are covered at the integration level
# (tests/integration/test_open_interest_repository.py) against a real
# Postgres, matching how FundingRateRepository is tested.
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from quant_hub.domain.market_data.entities import AssetRef, OpenInterest, RawOpenInterest
from quant_hub.infrastructure.market_data.ccxt_connector import CCXTConnector


def test_raw_open_interest_defaults() -> None:
    row = RawOpenInterest(
        asset=AssetRef(symbol="BTC/USDT:USDT", exchange="binance", asset_class="crypto", instrument_type="PERPETUAL"),
        ts=datetime(2026, 7, 14, tzinfo=timezone.utc),
        open_interest_usdt=Decimal("1000.5"),
    )
    assert row.open_interest_contracts is None
    assert row.source is None
    assert row.data_quality == "CLEAN"


def test_open_interest_defaults() -> None:
    row = OpenInterest(
        asset_id=__import__("uuid").uuid4(),
        ts=datetime(2026, 7, 14, tzinfo=timezone.utc),
        open_interest_usdt=Decimal("1000.5"),
    )
    assert row.open_interest_contracts is None
    assert row.data_quality == "CLEAN"


class _FakeExchange:
    """Minimal duck-typed stand-in for ccxt's async exchange client — no
    network I/O, just returns canned rows shaped like ccxt's unified
    fetch_open_interest_history response."""

    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows
        self.calls: list[tuple[str, int | None, int]] = []

    async def fetch_open_interest_history(self, symbol: str, since=None, limit: int = 500):
        self.calls.append((symbol, since, limit))
        return self._rows

    async def close(self) -> None:
        pass


@pytest.fixture
def connector() -> CCXTConnector:
    conn = CCXTConnector.__new__(CCXTConnector)  # bypass __init__ (no real aiohttp session)
    conn.source_id = "binance"
    return conn


@pytest.mark.asyncio
async def test_fetch_open_interest_history_maps_real_ccxt_shape(connector: CCXTConnector) -> None:
    # Shape live-verified against Binance 2026-07-14 (see connector docstring).
    connector._exchange = _FakeExchange([
        {
            "symbol": "BTC/USDT:USDT",
            "timestamp": 1784008800000,
            "openInterestAmount": 106325.509,
            "openInterestValue": 6666884964.56092,
        }
    ])

    rows = await connector.fetch_open_interest_history("BTC/USDT:USDT", limit=5)

    assert len(rows) == 1
    row = rows[0]
    assert row.open_interest_usdt == Decimal("6666884964.56092")
    assert row.open_interest_contracts == Decimal("106325.509")
    assert row.ts == datetime.fromtimestamp(1784008800000 / 1000, tz=timezone.utc)
    assert row.asset.instrument_type == "PERPETUAL"
    assert row.source == "binance"


@pytest.mark.asyncio
async def test_fetch_open_interest_history_skips_rows_missing_timestamp_or_value(connector: CCXTConnector) -> None:
    connector._exchange = _FakeExchange([
        {"timestamp": None, "openInterestValue": 100.0},  # missing timestamp
        {"timestamp": 1784008800000, "openInterestValue": None},  # missing notional
        {"timestamp": 1784008800000, "openInterestValue": 100.0},  # valid
    ])

    rows = await connector.fetch_open_interest_history("BTC/USDT:USDT")

    assert len(rows) == 1
    assert rows[0].open_interest_usdt == Decimal("100.0")


@pytest.mark.asyncio
async def test_fetch_open_interest_history_contracts_nullable_when_absent(connector: CCXTConnector) -> None:
    # A connector/exchange that only reports notional value, not contract count.
    connector._exchange = _FakeExchange([
        {"timestamp": 1784008800000, "openInterestValue": 100.0}
    ])

    rows = await connector.fetch_open_interest_history("BTC/USDT:USDT")

    assert rows[0].open_interest_contracts is None

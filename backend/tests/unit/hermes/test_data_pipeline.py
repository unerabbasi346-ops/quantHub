# Unit tests for hermes/monitors/data_pipeline.py — DB mocked, no live
# connection. Verifies the fresh/stale/dead staleness bucketing (task spec:
# green <1h, amber 1-24h, red >24h) off a mocked query result.
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from quant_hub.hermes.monitors.data_pipeline import (
    STATUS_DEAD,
    STATUS_FRESH,
    STATUS_STALE,
    get_asset_freshness,
    get_funding_freshness,
)


def _session_returning(rows: list) -> AsyncMock:
    session = AsyncMock()
    result = MagicMock()
    result.all.return_value = rows
    session.execute = AsyncMock(return_value=result)
    return session


@pytest.mark.asyncio
async def test_asset_freshness_buckets_fresh_stale_dead() -> None:
    now = datetime.now(timezone.utc)
    rows = [
        SimpleNamespace(asset_id="a1", symbol="BTC/USDT", instrument_type="SPOT", last_bar_ts=now - timedelta(minutes=30), bar_count=100),
        SimpleNamespace(asset_id="a2", symbol="ETH/USDT", instrument_type="SPOT", last_bar_ts=now - timedelta(hours=12), bar_count=50),
        SimpleNamespace(asset_id="a3", symbol="DEAD/USDT", instrument_type="SPOT", last_bar_ts=now - timedelta(hours=48), bar_count=10),
        SimpleNamespace(asset_id="a4", symbol="NEVER/USDT", instrument_type="SPOT", last_bar_ts=None, bar_count=0),
    ]
    session = _session_returning(rows)

    result = await get_asset_freshness(session)

    by_symbol = {r.symbol: r for r in result}
    assert by_symbol["BTC/USDT"].status == STATUS_FRESH
    assert by_symbol["ETH/USDT"].status == STATUS_STALE
    assert by_symbol["DEAD/USDT"].status == STATUS_DEAD
    assert by_symbol["NEVER/USDT"].status == STATUS_DEAD
    assert by_symbol["NEVER/USDT"].staleness_seconds is None


@pytest.mark.asyncio
async def test_funding_freshness_only_covers_rows_the_query_returns() -> None:
    now = datetime.now(timezone.utc)
    rows = [
        SimpleNamespace(asset_id="p1", symbol="BTC/USDT:USDT", last_funding_ts=now - timedelta(hours=2)),
    ]
    session = _session_returning(rows)

    result = await get_funding_freshness(session)

    assert len(result) == 1
    assert result[0].symbol == "BTC/USDT:USDT"
    assert result[0].status == STATUS_STALE  # 2h old -> amber per the 1h/24h thresholds

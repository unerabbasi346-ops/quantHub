# Unit tests for hermes/monitors/strategy_lifecycle.py — DB mocked, no live
# connection.
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from quant_hub.hermes.monitors.strategy_lifecycle import get_strategy_lifecycle


def _session_returning(rows: list) -> AsyncMock:
    session = AsyncMock()
    result = MagicMock()
    result.all.return_value = rows
    session.execute = AsyncMock(return_value=result)
    return session


@pytest.mark.asyncio
async def test_valid_rate_computed_from_signals_24h() -> None:
    rows = [
        SimpleNamespace(
            strategy_id="s1",
            name="reference-ma-crossover",
            status="ACTIVE",
            last_signal_ts=None,
            signals_24h=10,
            valid_signals_24h=8,
            latest_backtest_status="COMPLETED",
            latest_backtest_completed_at=None,
        ),
    ]
    session = _session_returning(rows)

    result = await get_strategy_lifecycle(session)

    assert len(result) == 1
    assert result[0].valid_rate_24h == pytest.approx(0.8)


@pytest.mark.asyncio
async def test_valid_rate_is_none_when_no_signals_in_window() -> None:
    rows = [
        SimpleNamespace(
            strategy_id="s2",
            name="quiet-strategy",
            status="ACTIVE",
            last_signal_ts=None,
            signals_24h=0,
            valid_signals_24h=None,
            latest_backtest_status=None,
            latest_backtest_completed_at=None,
        ),
    ]
    session = _session_returning(rows)

    result = await get_strategy_lifecycle(session)

    assert result[0].signals_24h == 0
    assert result[0].valid_rate_24h is None

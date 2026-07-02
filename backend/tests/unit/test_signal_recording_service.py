# Governing specification: Doc 14 §10.6.4 — Signal Validation, Signal Recording
# Per Doc 00 §14.11
#
# Proves SignalRecordingService wires validate -> record end-to-end (fakes,
# no DB needed), and specifically that INVALID signals are still recorded
# (Doc 14 §10.6.4: "Every generated signal recorded ... with ... validation
# status") — the critical behavioral difference from the Step 1.6
# reject-and-drop pattern for bars/ticks.
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from quant_hub.application.strategy_engine.signal_recording_service import (
    SignalRecordingService,
)
from quant_hub.domain.market_data.entities import AssetRef
from quant_hub.domain.strategy_engine.entities import RecordedSignal, Signal
from quant_hub.domain.strategy_engine.validation import VALIDATION_INVALID, VALIDATION_VALID

_ASSET = AssetRef(symbol="BTC/USDT", exchange="binance", asset_class="crypto")
_STRATEGY_ID = uuid.uuid4()
_ASSET_ID = uuid.uuid4()


class _FakeSignalRepository:
    def __init__(self, latest: RecordedSignal | None = None) -> None:
        self.latest = latest
        self.recorded: list[tuple[uuid.UUID, uuid.UUID, Signal, str]] = []

    async def get_latest(self, strategy_id, asset_id):
        return self.latest

    async def record(self, strategy_id, asset_id, signal, validation_status) -> uuid.UUID:
        self.recorded.append((strategy_id, asset_id, signal, validation_status))
        return uuid.uuid4()


def _signal(**overrides: object) -> Signal:
    defaults: dict[str, object] = dict(
        asset=_ASSET, value=Decimal("0.5"), ts=datetime.now(timezone.utc)
    )
    defaults.update(overrides)
    return Signal(**defaults)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_valid_signal_is_recorded_as_valid() -> None:
    repo = _FakeSignalRepository()
    service = SignalRecordingService(repo)

    recorded = await service.record_signal(_STRATEGY_ID, _ASSET_ID, _signal())

    assert recorded.validation_status == VALIDATION_VALID
    assert len(repo.recorded) == 1
    assert repo.recorded[0][3] == VALIDATION_VALID


@pytest.mark.asyncio
async def test_invalid_signal_is_still_recorded_not_dropped(caplog) -> None:
    # Doc 14 §10.6.4: "Every generated signal recorded" — unlike Step 1.6's
    # bars/ticks, an invalid signal must NOT be silently dropped.
    invalid = _signal(value=Decimal("5.0"))  # outside [-1, 1]
    repo = _FakeSignalRepository()
    service = SignalRecordingService(repo)

    with caplog.at_level(logging.WARNING):
        recorded = await service.record_signal(_STRATEGY_ID, _ASSET_ID, invalid)

    assert recorded.validation_status == VALIDATION_INVALID
    assert len(repo.recorded) == 1  # recorded, not dropped
    assert repo.recorded[0][3] == VALIDATION_INVALID
    warnings = [r for r in caplog.records if r.levelname == "WARNING"]
    assert len(warnings) == 1
    assert "recording invalid signal" in warnings[0].getMessage()


@pytest.mark.asyncio
async def test_rate_of_change_uses_previous_from_repository() -> None:
    previous = RecordedSignal(
        id=uuid.uuid4(),
        strategy_id=_STRATEGY_ID,
        asset_id=_ASSET_ID,
        value=Decimal("-1.0"),
        ts=datetime.now(timezone.utc) - timedelta(minutes=1),
        validation_status=VALIDATION_VALID,
    )
    repo = _FakeSignalRepository(latest=previous)
    service = SignalRecordingService(repo)

    # Full swing -1.0 -> 1.0 exceeds the 1.0 rate-of-change threshold.
    recorded = await service.record_signal(_STRATEGY_ID, _ASSET_ID, _signal(value=Decimal("1.0")))

    assert recorded.validation_status == VALIDATION_INVALID

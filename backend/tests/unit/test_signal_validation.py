# Governing specification: Doc 14 §10.6.4 — Signal Generation Pipeline, Signal Validation
# Per Doc 00 §14.11
#
# No database needed — pure logic on domain/strategy_engine/validation.py.
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from quant_hub.domain.market_data.entities import AssetRef
from quant_hub.domain.strategy_engine.entities import RecordedSignal, Signal
from quant_hub.domain.strategy_engine.validation import validate_signal
from uuid import uuid4

_ASSET = AssetRef(symbol="BTC/USDT", exchange="binance", asset_class="crypto")


def _signal(**overrides: object) -> Signal:
    defaults: dict[str, object] = dict(
        asset=_ASSET, value=Decimal("0.5"), ts=datetime.now(timezone.utc)
    )
    defaults.update(overrides)
    return Signal(**defaults)  # type: ignore[arg-type]


def _recorded(**overrides: object) -> RecordedSignal:
    defaults: dict[str, object] = dict(
        id=uuid4(),
        strategy_id=uuid4(),
        asset_id=uuid4(),
        value=Decimal("0.5"),
        ts=datetime.now(timezone.utc) - timedelta(minutes=1),
        validation_status="VALID",
    )
    defaults.update(overrides)
    return RecordedSignal(**defaults)  # type: ignore[arg-type]


def test_valid_signal_with_no_history_passes() -> None:
    assert validate_signal(_signal()).is_valid is True


def test_rejects_missing_asset_fields() -> None:
    result = validate_signal(_signal(asset=AssetRef(symbol="", exchange="", asset_class="crypto")))
    assert result.is_valid is False
    assert any("asset.symbol" in e for e in result.errors)
    assert any("asset.exchange" in e for e in result.errors)


def test_rejects_future_timestamp_beyond_tolerance() -> None:
    result = validate_signal(_signal(ts=datetime.now(timezone.utc) + timedelta(hours=1)))
    assert result.is_valid is False
    assert any("future" in e for e in result.errors)


def test_accepts_small_future_skew_within_tolerance() -> None:
    result = validate_signal(_signal(ts=datetime.now(timezone.utc) + timedelta(seconds=30)))
    assert result.is_valid is True


def test_rejects_value_outside_bounds() -> None:
    assert validate_signal(_signal(value=Decimal("1.5"))).is_valid is False
    assert validate_signal(_signal(value=Decimal("-1.5"))).is_valid is False


def test_accepts_value_at_bounds() -> None:
    assert validate_signal(_signal(value=Decimal("1"))).is_valid is True
    assert validate_signal(_signal(value=Decimal("-1"))).is_valid is True


def test_rejects_non_finite_value() -> None:
    result = validate_signal(_signal(value=Decimal("NaN")))
    assert result.is_valid is False
    assert any("finite" in e for e in result.errors)


def test_rate_of_change_within_threshold_passes() -> None:
    previous = _recorded(value=Decimal("0.0"))
    result = validate_signal(_signal(value=Decimal("0.9")), previous=previous)
    assert result.is_valid is True


def test_rate_of_change_beyond_threshold_rejected() -> None:
    previous = _recorded(value=Decimal("-1.0"))
    result = validate_signal(_signal(value=Decimal("1.0")), previous=previous)
    assert result.is_valid is False
    assert any("rate-of-change" in e for e in result.errors)


def test_out_of_order_ts_against_previous_rejected() -> None:
    previous = _recorded(ts=datetime.now(timezone.utc))
    result = validate_signal(
        _signal(ts=previous.ts - timedelta(minutes=5), value=previous.value), previous=previous
    )
    assert result.is_valid is False
    assert any("inconsistent with recorded history" in e for e in result.errors)


def test_no_history_skips_rate_of_change_and_ordering_checks() -> None:
    # A strategy's very first signal for an instrument has nothing to be
    # inconsistent with — previous=None must never fail these two checks.
    result = validate_signal(_signal(value=Decimal("1.0")), previous=None)
    assert result.is_valid is True

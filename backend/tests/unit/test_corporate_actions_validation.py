# Governing specification: Doc 11 §5/§3 — Data Validation Engine / Corporate Actions
# Per Doc 00 §14.11
from __future__ import annotations

from datetime import date
from decimal import Decimal

from quant_hub.domain.market_data.entities import AssetRef, RawCorporateAction
from quant_hub.domain.market_data.validation import validate_corporate_action

_ASSET = AssetRef(symbol="AAPL", exchange="yfinance", asset_class="equity")


def _action(**overrides: object) -> RawCorporateAction:
    defaults: dict[object, object] = dict(
        asset=_ASSET, action_type="DIVIDEND", ex_date=date(2026, 5, 11), amount=Decimal("0.27")
    )
    defaults.update(overrides)
    return RawCorporateAction(**defaults)  # type: ignore[arg-type]


def test_valid_dividend_passes() -> None:
    assert validate_corporate_action(_action()).is_valid is True


def test_valid_split_passes() -> None:
    result = validate_corporate_action(
        _action(action_type="SPLIT", amount=None, ratio=Decimal("4"))
    )
    assert result.is_valid is True


def test_rejects_missing_ratio_and_amount() -> None:
    result = validate_corporate_action(_action(amount=None, ratio=None))
    assert result.is_valid is False
    assert any("no adjustment data" in e for e in result.errors)


def test_rejects_negative_amount() -> None:
    result = validate_corporate_action(_action(amount=Decimal("-1")))
    assert result.is_valid is False
    assert any("amount" in e for e in result.errors)


def test_rejects_zero_ratio() -> None:
    result = validate_corporate_action(
        _action(action_type="SPLIT", amount=None, ratio=Decimal("0"))
    )
    assert result.is_valid is False
    assert any("ratio" in e for e in result.errors)


def test_rejects_empty_action_type() -> None:
    result = validate_corporate_action(_action(action_type=""))
    assert result.is_valid is False
    assert any("action_type" in e for e in result.errors)


def test_reverse_split_ratio_below_one_is_valid() -> None:
    # A 1-for-10 reverse split is a valid ratio (0.1), not an error.
    result = validate_corporate_action(
        _action(action_type="REVERSE_SPLIT", amount=None, ratio=Decimal("0.1"))
    )
    assert result.is_valid is True

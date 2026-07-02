# Governing specification: Doc 11 §3 — Corporate Actions Processing (wiring)
# Per Doc 00 §14.11
#
# Proves CorporateActionsIngestionService actually wires Acquire ->
# Validate -> Persist end-to-end (fakes, no DB/network needed).
from __future__ import annotations

import logging
import uuid
from datetime import date
from decimal import Decimal

import pytest

from quant_hub.application.market_data.corporate_actions_service import (
    CorporateActionsIngestionService,
)
from quant_hub.domain.market_data.entities import AssetRef, CorporateAction, RawCorporateAction
from quant_hub.infrastructure.market_data.retry import RetryExhaustedError

_ASSET = AssetRef(symbol="AAPL", exchange="yfinance", asset_class="equity")
_ASSET_ID = uuid.uuid4()


class _FakeConnector:
    source_id = "yfinance"

    def __init__(self, actions=None, exhausted: bool = False) -> None:
        self._actions = actions or []
        self._exhausted = exhausted

    async def fetch_corporate_actions(self, symbol):
        if self._exhausted:
            raise RetryExhaustedError(context="test", attempts=3, last_error=Exception("boom"))
        return self._actions


class _FakeAssetRepository:
    async def get_by_id(self, asset_id):
        return None

    async def get_by_symbol_exchange(self, symbol, exchange):
        return None

    async def list_active(self):
        return []

    async def upsert(self, asset: AssetRef):
        return _ASSET_ID


class _FakeCorporateActionsRepository:
    def __init__(self) -> None:
        self.persisted: list[CorporateAction] = []

    async def get_by_asset(self, asset_id):
        return []

    async def upsert_actions(self, actions: list[CorporateAction]) -> int:
        self.persisted.extend(actions)
        return len(actions)


def _dividend(**overrides: object) -> RawCorporateAction:
    defaults: dict[object, object] = dict(
        asset=_ASSET, action_type="DIVIDEND", ex_date=date(2026, 5, 11), amount=Decimal("0.27")
    )
    defaults.update(overrides)
    return RawCorporateAction(**defaults)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_valid_action_is_persisted() -> None:
    connector = _FakeConnector(actions=[_dividend()])
    assets, repo = _FakeAssetRepository(), _FakeCorporateActionsRepository()
    service = CorporateActionsIngestionService(connector, assets, repo)

    count = await service.ingest_corporate_actions("AAPL")

    assert count == 1
    assert len(repo.persisted) == 1
    assert repo.persisted[0].amount == Decimal("0.27")


@pytest.mark.asyncio
async def test_invalid_action_rejected_not_persisted_and_logged(caplog) -> None:
    invalid = _dividend(amount=Decimal("-1"))
    connector = _FakeConnector(actions=[_dividend(), invalid])
    assets, repo = _FakeAssetRepository(), _FakeCorporateActionsRepository()
    service = CorporateActionsIngestionService(connector, assets, repo)

    with caplog.at_level(logging.WARNING):
        count = await service.ingest_corporate_actions("AAPL")

    assert count == 1  # only the valid one
    assert len(repo.persisted) == 1
    warnings = [r for r in caplog.records if r.levelname == "WARNING"]
    assert len(warnings) == 1
    assert "rejected invalid action" in warnings[0].getMessage()


@pytest.mark.asyncio
async def test_acquire_failure_logged_and_returns_zero(caplog) -> None:
    connector = _FakeConnector(exhausted=True)
    assets, repo = _FakeAssetRepository(), _FakeCorporateActionsRepository()
    service = CorporateActionsIngestionService(connector, assets, repo)

    with caplog.at_level(logging.ERROR):
        count = await service.ingest_corporate_actions("AAPL")

    assert count == 0
    assert repo.persisted == []
    errors = [r for r in caplog.records if r.levelname == "ERROR"]
    assert len(errors) == 1
    assert "acquire failed after retries" in errors[0].getMessage()


@pytest.mark.asyncio
async def test_no_actions_returns_zero_without_asset_upsert() -> None:
    connector = _FakeConnector(actions=[])
    assets, repo = _FakeAssetRepository(), _FakeCorporateActionsRepository()
    service = CorporateActionsIngestionService(connector, assets, repo)

    count = await service.ingest_corporate_actions("AAPL")

    assert count == 0
    assert repo.persisted == []

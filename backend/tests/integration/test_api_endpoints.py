# Governing specification: Doc 07 §API Standards; Doc 10 §Response Envelope.
# Doc 00 §14.11.
#
# Endpoint-level integration tests for the three write/compute endpoints added
# in the owner feature push — the dedicated tests Step 4.3's precedent calls
# for whenever a new write/compute endpoint lands:
#   - GET  /v1/markets/correlation        (compute: price-return correlation)
#   - PATCH /v1/strategies/{id}/status     (write:  governed lifecycle transition)
#   - PUT  /v1/portfolios/{id}/capital     (write:  operator-set capital, F-19)
#
# They drive the REAL FastAPI app through httpx's ASGITransport, with
# get_session overridden to a single test-scoped session bound to a connection
# whose outer transaction is rolled back at teardown (join_transaction_mode=
# "create_savepoint" so the endpoints' own commit() releases a savepoint rather
# than escaping isolation). Nothing touches the shared dev data permanently.
from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from quant_hub.config import settings
from quant_hub.infrastructure.database import get_session
from quant_hub.main import app


@pytest_asyncio.fixture
async def api() -> AsyncIterator[tuple[AsyncClient, AsyncSession]]:
    engine = create_async_engine(settings.database_url)
    conn = await engine.connect()
    trans = await conn.begin()
    session = AsyncSession(bind=conn, join_transaction_mode="create_savepoint")

    async def _override_get_session() -> AsyncIterator[AsyncSession]:
        # Same session for every request in the test so seeds and the endpoint
        # share one connection (and one rolled-back outer transaction).
        yield session

    app.dependency_overrides[get_session] = _override_get_session
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client, session
    finally:
        app.dependency_overrides.clear()
        await session.close()
        await trans.rollback()
        await conn.close()
        await engine.dispose()


# ── GET /v1/markets/correlation ─────────────────────────────────────────────
@pytest.mark.asyncio
async def test_correlation_matrix_over_two_aligned_assets(api) -> None:
    client, session = api
    # Isolate: hide the pre-existing dev assets so the endpoint sees only the
    # two we control (rolled back at teardown).
    await session.execute(text("UPDATE market_data.assets SET is_active = FALSE WHERE is_active = TRUE"))

    async def seed_asset(symbol: str) -> str:
        row = await session.execute(
            text(
                "INSERT INTO market_data.assets (symbol, exchange, asset_class, currency) "
                "VALUES (:s, 'test', 'crypto', 'USD') RETURNING id"
            ),
            {"s": symbol},
        )
        return str(row.scalar_one())

    a_id = await seed_asset("AAA/USD")
    b_id = await seed_asset("BBB/USD")

    # Five aligned 1h bars; BBB tracks AAA closely (strongly positive returns corr).
    a_closes = [100.0, 102.0, 101.0, 104.0, 106.0]
    b_closes = [200.0, 204.5, 201.5, 208.0, 212.0]
    for i, (ca, cb) in enumerate(zip(a_closes, b_closes)):
        for aid, close in ((a_id, ca), (b_id, cb)):
            await session.execute(
                text(
                    "INSERT INTO market_data.ohlcv_bars "
                    "(asset_id, interval, ts, open, high, low, close, volume, adjustment_factor, data_quality) "
                    "VALUES (:aid, '1h', :ts, :c, :c, :c, :c, 1, 1, 'CLEAN')"
                ),
                {"aid": aid, "ts": datetime(2030, 1, 1, i, 0, tzinfo=timezone.utc), "c": close},
            )

    resp = await client.get("/v1/markets/correlation", params={"interval": "1h"})
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["interval"] == "1h"
    assert body["sample_size"] == 4  # 5 aligned prices -> 4 returns
    symbols = {a["symbol"] for a in body["assets"]}
    assert symbols == {"AAA/USD", "BBB/USD"}
    n = len(body["assets"])
    assert n == 2
    # diagonal is 1.0
    for i in range(n):
        assert body["matrix"][i][i] == 1.0
    # off-diagonal defined, bounded, symmetric, and strongly positive here
    r = body["matrix"][0][1]
    assert r is not None and -1.0 <= r <= 1.0
    assert r == body["matrix"][1][0]
    assert r > 0.8


# ── PATCH /v1/strategies/{id}/status ────────────────────────────────────────
async def _seed_strategy(session: AsyncSession, name: str) -> str:
    row = await session.execute(
        text(
            "INSERT INTO core.strategies (name, version, config) "
            "VALUES (:n, '1.0.0', '{}'::jsonb) RETURNING id"
        ),
        {"n": name},
    )
    return str(row.scalar_one())


@pytest.mark.asyncio
async def test_activate_then_deactivate_strategy(api) -> None:
    client, session = api
    sid = await _seed_strategy(session, "status-write-test")

    r1 = await client.patch(f"/v1/strategies/{sid}/status", json={"status": "ACTIVE"})
    assert r1.status_code == 200
    assert r1.json()["data"]["status"] == "ACTIVE"

    r2 = await client.patch(f"/v1/strategies/{sid}/status", json={"status": "INACTIVE"})
    assert r2.status_code == 200
    assert r2.json()["data"]["status"] == "INACTIVE"

    # persisted: a plain GET reflects the last transition
    r3 = await client.get(f"/v1/strategies/{sid}")
    assert r3.json()["data"]["status"] == "INACTIVE"


@pytest.mark.asyncio
async def test_invalid_status_is_rejected(api) -> None:
    client, session = api
    sid = await _seed_strategy(session, "status-reject-test")
    resp = await client.patch(f"/v1/strategies/{sid}/status", json={"status": "HALTED"})
    assert resp.status_code == 400
    assert resp.json()["error"]["error_code"] == "ValidationError"


@pytest.mark.asyncio
async def test_status_unknown_strategy_404(api) -> None:
    client, _ = api
    resp = await client.patch(
        "/v1/strategies/00000000-0000-0000-0000-000000000000/status",
        json={"status": "ACTIVE"},
    )
    assert resp.status_code == 404


# ── PUT /v1/portfolios/{id}/capital ─────────────────────────────────────────
async def _seed_portfolio(session: AsyncSession, name: str) -> str:
    row = await session.execute(
        text(
            "INSERT INTO core.portfolios (name, base_currency, portfolio_type, is_active) "
            "VALUES (:n, 'USD', 'LIVE', TRUE) RETURNING id"
        ),
        {"n": name},
    )
    return str(row.scalar_one())


@pytest.mark.asyncio
async def test_set_configured_capital(api) -> None:
    client, session = api
    pid = await _seed_portfolio(session, "capital-write-test")

    resp = await client.put(
        f"/v1/portfolios/{pid}/capital", json={"configured_capital": "250000.50"}
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["configured_capital"] == "250000.50000000"

    # persisted: a plain GET reflects the configured figure
    got = await client.get(f"/v1/portfolios/{pid}")
    assert got.json()["data"]["configured_capital"] == "250000.50000000"


@pytest.mark.asyncio
async def test_non_positive_capital_rejected(api) -> None:
    client, session = api
    pid = await _seed_portfolio(session, "capital-reject-test")
    resp = await client.put(f"/v1/portfolios/{pid}/capital", json={"configured_capital": "0"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_capital_unknown_portfolio_404(api) -> None:
    client, _ = api
    resp = await client.put(
        "/v1/portfolios/00000000-0000-0000-0000-000000000000/capital",
        json={"configured_capital": "1000"},
    )
    assert resp.status_code == 404


# ── GET /v1/assets/{id}/open-interest (migration b4f8e21ac9d3) ─────────────
async def _seed_asset(session: AsyncSession, symbol: str, instrument_type: str) -> str:
    row = await session.execute(
        text(
            "INSERT INTO market_data.assets (symbol, exchange, asset_class, currency, instrument_type) "
            "VALUES (:s, 'test', 'crypto', 'USD', :it) RETURNING id"
        ),
        {"s": symbol, "it": instrument_type},
    )
    return str(row.scalar_one())


@pytest.mark.asyncio
async def test_open_interest_returns_real_data_for_perpetual(api) -> None:
    client, session = api
    asset_id = await _seed_asset(session, "OITEST/USDT:USDT", "PERPETUAL")
    await session.execute(
        text(
            "INSERT INTO market_data.open_interest "
            "(asset_id, ts, open_interest_usdt, open_interest_contracts) "
            "VALUES (:a, :t, :usdt, :contracts)"
        ),
        {
            "a": asset_id,
            "t": datetime(2026, 7, 14, tzinfo=timezone.utc),
            "usdt": "6666884964.56092",
            "contracts": "106325.509",
        },
    )

    resp = await client.get(f"/v1/assets/{asset_id}/open-interest")

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["asset_id"] == asset_id
    assert data[0]["open_interest_usdt"] == "6666884964.56092000"
    assert data[0]["open_interest_contracts"] == "106325.50900000"


@pytest.mark.asyncio
async def test_open_interest_404s_for_spot_instrument(api) -> None:
    client, session = api
    asset_id = await _seed_asset(session, "OISPOT/USDT", "SPOT")

    resp = await client.get(f"/v1/assets/{asset_id}/open-interest")

    assert resp.status_code == 404
    body = resp.json()
    assert "SPOT" in body["error"]["message"]


@pytest.mark.asyncio
async def test_open_interest_unknown_asset_404(api) -> None:
    client, _ = api
    resp = await client.get("/v1/assets/00000000-0000-0000-0000-000000000000/open-interest")
    assert resp.status_code == 404

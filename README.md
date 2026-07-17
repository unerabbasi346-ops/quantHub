# QuantHub

A modular, multi-strategy quantitative trading platform — built from a 25-file engineering handbook, implemented phase by phase, with every architectural decision, scope boundary, and known limitation tracked and version-controlled.

> **Status:** Active development. Phases 0–4 complete and regression-tested. Phase 5 (paper trading) in progress. See [Project Status](#project-status) below.

---

## What this is

QuantHub is a platform for running, testing, and monitoring quantitative trading strategies — not a single trading bot. Strategies plug into the platform through a governed interface; the platform itself handles market data ingestion, risk management, order execution, and portfolio tracking identically regardless of which strategy is running.

It's built around a strict separation of concerns: strategy logic is never coupled to platform infrastructure. A reference moving-average-crossover strategy exists purely to prove the plugin interface works end-to-end — it is explicitly not intended to be economically meaningful.

**This project is a learning platform, not investment advice.** Nothing here should be used to make real trading decisions. See [Disclaimer](#disclaimer).

---

## Why it's built this way


**Backend:** Python, FastAPI, PostgreSQL, SQLAlchemy, Alembic, Redis
**Frontend:** Next.js, React, TypeScript, Tailwind CSS, TanStack Query, TradingView Lightweight Charts
**Infrastructure:** Docker, Alembic-managed migrations, pytest

5-layer backend architecture (Presentation -> Application -> Domain -> Infrastructure -> Persistence), with a strict rule: the domain layer defines interfaces, infrastructure implements them, and nothing outside a strategy plugin ever assumes a specific strategy's logic.

---

## Project Status

| Phase | Scope | Status |
|---|---|---|
| 0 | Repo scaffold, dependencies, DB schema, backend/frontend skeletons, fail-safe risk gate | Complete |
| 1 | Live market data ingestion (CCXT/yfinance), validation, quality scoring, error recovery, corporate actions | Complete |
| 2 | Strategy plugin interface, Signal contract, strategy registry, reference strategy | Complete |
| 3A | Full trade-execution loop: Sizing -> Construction -> Order -> Risk Gate -> Fill -> Position -> P&L -> Backtest | Complete |
| 3B | ML Engineering + Research Engineering | Deliberately deferred - no runtime consumer yet (S-7) |
| 4 | Dashboard - live market charts, portfolio, execution blotter, strategy/signal/backtest views, risk monitoring | Complete |
| 5 | Paper trading validation gate | In progress |

Every phase above was closed with a full regression pass: complete test suite, fresh-database migration from empty, and a live end-to-end run against real ingested market data - not mocks.

---

## Getting started

**Prerequisites:** Python 3.12+, Node.js 20+, Docker, PostgreSQL 17 (via Docker)

```bash
# Clone
git clone https://github.com/<your-username>/quanthub.git
cd quanthub

# Start Postgres + Redis
cd docker && docker compose up -d && cd ..

# Backend
cd backend
pip install -e . --break-system-packages
alembic upgrade head
PYTHONPATH=src uvicorn quant_hub.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Visit `http://localhost:3000` for the dashboard, `http://localhost:8000/v1/health` to confirm the backend is running.

Run the test suite (one-time setup: a dedicated `<db>_test` database, kept
schema-isolated from your dev data — tests/conftest.py derives its name from
`DATABASE_URL` automatically, so nothing in .env changes):
```bash
cd backend
createdb quant_hub_test   # or: docker exec <postgres-container> psql -U quant_hub -d postgres -c "CREATE DATABASE quant_hub_test OWNER quant_hub"
DATABASE_URL=postgresql://quant_hub:<password>@localhost:5432/quant_hub_test alembic upgrade head
PYTHONPATH=src pytest tests/
```

---

## Known limitations

This project tracks every scope decision, deferred requirement, and structural gap explicitly rather than hiding them. See [`handbook/KNOWN_LIMITATIONS.md`](handbook/KNOWN_LIMITATIONS.md) for the full, honestly-maintained list.

If a limitation is listed there, it's a known, deliberate, tracked gap - not an oversight.

---

## Disclaimer

QuantHub is an educational and portfolio project. It is **not financial advice**, is **not intended for live trading with real capital**, and makes **no claim of economic validity** for any strategy included in it, including the reference implementation. Trading involves substantial risk of loss. Nothing in this repository should be construed as a recommendation to buy, sell, or hold any financial instrument.

---

## About

Built by a solo developer as a hands-on way to learn quantitative finance, systems architecture, and professional software engineering practices - from the ground up, one reviewed and verified phase at a time.

## License

MIT

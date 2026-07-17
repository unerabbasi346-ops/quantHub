# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# §Configuration: DATABASE_URL from environment, never hardcoded.
#
# ROOT-LEVEL, runs before every other conftest.py / test module in this
# directory tree — pytest imports it first. That ordering is load-bearing:
# quant_hub.infrastructure.database builds its module-level `engine` /
# AsyncSessionLocal from quant_hub.config.settings.database_url AT IMPORT
# TIME, and api/ml.py's background training jobs call AsyncSessionLocal()
# directly (bypassing FastAPI's get_session dependency override entirely —
# see tests/integration/test_ml_api.py's module docstring). There is no way
# to redirect that path per-test. Redirecting DATABASE_URL itself, before
# quant_hub.config is ever imported, is the only point that reaches every
# write path (repository fixtures AND the background-task session) uniformly.
#
# WAS: pytest ran straight against .env's DATABASE_URL — the live dev DB.
# test_ml_api.py's end-to-end training test (real app, real background task)
# left real accuracy=1.0 XGBoost_MetaLabeler rows in analytics.ml_models
# after every run; two separate cleanups of that pollution are recorded in
# this session's memory. The other integration tests were already
# transaction-scoped (rollback at teardown) and never leaked — only the
# AsyncSessionLocal bypass did.
#
# FIX: derive a same-cluster `<name>_test` database from .env's DATABASE_URL
# (no separate .env.test to keep in sync — works for any dev's DB name) and
# force it into os.environ before anything imports quant_hub.*. The database
# itself is provisioned once, out of band: `createdb quant_hub_test` (or
# `docker exec ... psql -c "CREATE DATABASE quant_hub_test OWNER quant_hub"`)
# then `DATABASE_URL=...quant_hub_test alembic upgrade head` — same migrations
# as the real DB, per Doc 09 §Migration Strategy's "migrations are the
# source of truth for schema, including test schema."
from __future__ import annotations

import os
import re
from pathlib import Path

from dotenv import dotenv_values


def _test_database_url() -> str:
    base = os.environ.get("DATABASE_URL") or dotenv_values(Path(__file__).resolve().parents[1] / ".env").get(
        "DATABASE_URL", ""
    )
    if not base:
        raise RuntimeError(
            "No DATABASE_URL found (env var or backend/.env) — cannot derive a test database URL."
        )
    # .../quant_hub -> .../quant_hub_test (last path segment = DB name).
    test_url, n = re.subn(r"/([^/?]+)(\?.*)?$", lambda m: f"/{m.group(1)}_test{m.group(2) or ''}", base)
    if n != 1:
        raise RuntimeError(f"Could not derive a test database name from DATABASE_URL={base!r}")
    return test_url


_TEST_DB_URL = _test_database_url()
assert _TEST_DB_URL.rsplit("/", 1)[-1].split("?")[0].endswith("_test"), (
    f"Refusing to run tests against a non-test database: {_TEST_DB_URL!r}"
)
# Override BEFORE any quant_hub import in this process — quant_hub.config's
# Settings() and quant_hub.infrastructure.database's module-level engine are
# both built once, at first import, from whatever DATABASE_URL is visible now.
os.environ["DATABASE_URL"] = _TEST_DB_URL

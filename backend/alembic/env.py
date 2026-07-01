# =============================================================================
# Alembic migration environment
# Governing specification: Doc 09 §Migration Strategy (QH-009 v1.0)
# Doc 07 §Configuration: database URL from environment variable, never hardcoded
# Doc 09 §Security: credentials never in source code
# Per Doc 00 §14.11
# =============================================================================
from __future__ import annotations

import os
import re
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config

# Logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# target_metadata = None because SQLAlchemy ORM models are not yet defined.
# When persistence/models/ is implemented, import Base.metadata here to enable
# autogenerate. Until then, all migrations are hand-crafted.
# Doc 09 §Migration Strategy: Alembic is the authoritative migration path.
target_metadata = None


def get_url() -> str:
    """Resolve the synchronous (psycopg2) database URL.

    Priority:
    1. DATABASE_URL env var — expected to be a sync postgresql:// URL
    2. Strips +asyncpg from the app's async URL if DATABASE_URL is absent

    Doc 07 §Configuration: all config from environment variables.
    Doc 09 §Security: credentials never hardcoded.
    """
    raw = os.environ.get("DATABASE_URL", "")
    if not raw:
        # Fall back to app default but convert asyncpg → psycopg2
        raw = "postgresql+asyncpg://quant_hub:changeme@localhost:5432/quant_hub"
    # Convert asyncpg driver specifier to psycopg2 for synchronous Alembic use
    return re.sub(r"\+asyncpg", "", raw)


def run_migrations_offline() -> None:
    """Emit migration SQL without a live database connection (--sql mode).

    Produces SQL that can be reviewed before applying to production.
    Doc 09 §Migration Strategy: review migrations before applying.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Required: Alembic must know about all schemas to track non-public tables
        include_schemas=True,
        version_table_schema="public",
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Apply migrations against a live database connection."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        # NullPool: Alembic should not pool connections — one connection per run
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            version_table_schema="public",
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

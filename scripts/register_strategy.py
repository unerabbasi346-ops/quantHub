#!/usr/bin/env python
# Governing specification: Doc 14 §10.2.5/§10.2.8 (Strategy registration &
#   configuration); Doc 04 (scripts/ = automation utilities, no business logic).
#   P-1/T-2 (strategies are external, opaque units). Doc 00 §14.9 (no arbitrary
#   code execution). Per Doc 00 §14.11
#
# SEMI-AUTOMATIC STRATEGY REGISTRATION (owner decision, Option A). One explicit
# command registers a strategy so it appears in the UI registry (core.strategies,
# read by GET /v1/strategies). This deliberately does NOT scan the
# reference_strategies/ folder and auto-load whatever it finds — that would
# re-open the exact security boundary the Step 2.4 plugin registry closed
# (a dropped file must never auto-execute; Doc 00 §14.9). Registration is always
# an explicit, human-run act.
#
# WHAT "REGISTER" DOES, per strategy:
#   1. register_plugin(name, cls)  — binds the runtime plugin (in-process).
#   2. StrategyRepository.upsert(StrategyRef(...))  — writes/refreshes the
#      core.strategies row (name, version, description, config) so the UI lists
#      it. Status is NOT touched (a governed §10.2.6 transition, not set here),
#      so re-registering never silently activates/deactivates a strategy.
#
# TWO WAYS TO CALL IT (both one command, both explicit):
#   A) Known strategies from the MANIFEST below (the maintained set):
#        python scripts/register_strategy.py --all
#        python scripts/register_strategy.py reference-funding-basis
#        python scripts/register_strategy.py --list
#   B) A freshly dropped plugin file, named explicitly (no manifest edit):
#        python scripts/register_strategy.py \
#          --name reference-x --plugin \
#          quant_hub.application.strategy_engine.reference_strategies.x:XStrategy \
#          --version 1.0.0 --description "…" --config '{"symbol": "BTC/USDT:USDT"}'
#
# ADDING A NEW STRATEGY the simplest way: drop its file in
# application/strategy_engine/reference_strategies/, add ONE line to MANIFEST
# below (the explicit registration), then run `--all`. The manifest line IS the
# security boundary — the code that runs is exactly what a human listed here.
from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path

_BACKEND_SRC = Path(__file__).resolve().parent.parent / "backend" / "src"
sys.path.insert(0, str(_BACKEND_SRC))

from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from quant_hub.application.strategy_engine.reference_strategies.funding_rate_basis import (  # noqa: E402
    FundingRateBasisStrategy,
)
from quant_hub.application.strategy_engine.reference_strategies.moving_average_crossover import (  # noqa: E402
    MovingAverageCrossoverStrategy,
)
from quant_hub.domain.strategy_engine.entities import StrategyRef  # noqa: E402
from quant_hub.domain.strategy_engine.strategy import Strategy  # noqa: E402
from quant_hub.infrastructure.database import engine  # noqa: E402
from quant_hub.infrastructure.strategy_engine.plugin_registry import register_plugin  # noqa: E402
from quant_hub.persistence.repositories.strategy_engine import SQLAlchemyStrategyRepository  # noqa: E402


@dataclass(frozen=True)
class ManifestEntry:
    name: str
    plugin_cls: type[Strategy]
    version: str
    description: str
    config: dict[str, object]


# ── MANIFEST: the explicit, human-maintained list of registerable strategies.
#    Editing this list is the "registration" act (Option A). Nothing is loaded
#    from disk automatically. ─────────────────────────────────────────────────
MANIFEST: list[ManifestEntry] = [
    ManifestEntry(
        name="reference-ma-crossover",
        plugin_cls=MovingAverageCrossoverStrategy,
        version="1.0.0",
        description=(
            "Reference / testing strategy — a textbook moving-average crossover that "
            "validates the strategy pipeline. NOT a real trading strategy; kept for "
            "dev, testing and UI validation only."
        ),
        config={
            "symbol": "BTC/USDT",
            "exchange": "binance",
            "asset_class": "crypto",
            "interval": "1h",
            "short_window": 5,
            "long_window": 20,
        },
    ),
    ManifestEntry(
        name="reference-funding-basis",
        plugin_cls=FundingRateBasisStrategy,
        version="1.0.0",
        description=(
            "Perpetual funding-carry reference strategy — proves the perpetual funding "
            "data path end to end. Reference / testing strategy, not a real strategy."
        ),
        config={
            "symbol": "BTC/USDT:USDT",
            "exchange": "binance",
            "asset_class": "crypto",
            "window": 3,
        },
    ),
]
_BY_NAME = {e.name: e for e in MANIFEST}


def _load_plugin(path: str) -> type[Strategy]:
    """Resolve an explicit 'module.path:ClassName' to a Strategy subclass.

    Explicit only (Doc 00 §14.9): the caller names the exact class; nothing is
    discovered/guessed. Verified to be a Strategy subclass before use.
    """
    module_path, _, cls_name = path.partition(":")
    if not module_path or not cls_name:
        raise SystemExit(f"--plugin must be 'module.path:ClassName', got {path!r}")
    cls = getattr(importlib.import_module(module_path), cls_name)
    if not (isinstance(cls, type) and issubclass(cls, Strategy)):
        raise SystemExit(f"{path} is not a Strategy subclass")
    return cls


async def _register(entries: list[ManifestEntry]) -> None:
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            repo = SQLAlchemyStrategyRepository(session)
            for e in entries:
                register_plugin(e.name, e.plugin_cls)  # runtime binding
                strategy_id = await repo.upsert(
                    StrategyRef(name=e.name, version=e.version, description=e.description, config=e.config)
                )
                print(f"registered: {e.name} (v{e.version}) -> core.strategies id={strategy_id}")
            await session.commit()  # this script owns the transaction boundary
        print(f"done — {len(entries)} strateg{'y' if len(entries) == 1 else 'ies'} registered.")
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Explicitly register a strategy into the UI registry (Option A).")
    parser.add_argument("name", nargs="?", help="a MANIFEST strategy name to register")
    parser.add_argument("--all", action="store_true", help="register every strategy in the MANIFEST")
    parser.add_argument("--list", action="store_true", help="list MANIFEST strategy names and exit")
    # Explicit ad-hoc registration for a freshly dropped file (no manifest edit):
    parser.add_argument("--plugin", help="'module.path:ClassName' of the plugin to register")
    parser.add_argument("--version", default="1.0.0")
    parser.add_argument("--description", default="")
    parser.add_argument("--config", default="{}", help="JSON config object")
    args = parser.parse_args()

    if args.list:
        for e in MANIFEST:
            print(f"{e.name}\tv{e.version}\t{e.plugin_cls.__name__}")
        return

    if args.plugin:
        if not args.name:
            raise SystemExit("--plugin requires --name / a positional name")
        entry = ManifestEntry(
            name=args.name,
            plugin_cls=_load_plugin(args.plugin),
            version=args.version,
            description=args.description,
            config=json.loads(args.config),
        )
        asyncio.run(_register([entry]))
        return

    if args.all:
        asyncio.run(_register(MANIFEST))
        return

    if args.name:
        entry = _BY_NAME.get(args.name)
        if entry is None:
            raise SystemExit(f"unknown strategy {args.name!r}. Known: {', '.join(_BY_NAME)} (or use --plugin).")
        asyncio.run(_register([entry]))
        return

    parser.print_help()


if __name__ == "__main__":
    main()

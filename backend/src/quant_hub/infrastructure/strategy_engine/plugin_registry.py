# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Infrastructure — Doc 07 §Layers
# P-1, T-2: strategies are external, opaque units the platform serves uniformly
# Per Doc 00 §14.11
#
# Step 2.4: RESOLVES the open question deferred at Step 2.3 — "how does the
# Strategy Engine obtain a live Python object of the correct plugin class
# for a given core.strategies row?" (domain/strategy_engine/strategy.py's
# Strategy docstring, "STILL OPEN" note).
#
# JUDGMENT CALL (Doc 00 §14.5/§14.7 — flagged, proposed with a second real
# consumer — this reference strategy — now available to design against):
# a plain in-process dict, keyed by core.strategies.name, populated by
# EXPLICIT register_plugin() calls (bootstrap code, not import-time side
# effects — see scripts/run_reference_strategy.py) rather than:
#   - Dynamic class-path strings stored in core.strategies.config JSONB,
#     resolved via importlib: rejected — it would mean a database row can
#     name arbitrary Python code to execute, which is a real governance/
#     security concern (Doc 00 §14.9: "no ... arbitrary code execution")
#     for a column that Doc 14 §10.2.8 governs as strategy configuration,
#     not as a code-loading mechanism.
#   - A full plugin-package / setuptools entry-points discovery system:
#     rejected as premature — with exactly one reference plugin to design
#     around, building auto-discovery machinery would be speculative
#     scope Doc 00 §14.6 cautions against ("do not add architecture beyond
#     what's needed").
# REVISIT TRIGGER: once more than a small handful of plugins exist and a
# manually-maintained dict becomes unwieldy to keep in sync with
# registrations, reconsider entry-points-based discovery.
#
# `name` (core.strategies.name, UNIQUE per Step 1.1 schema) is reused as
# the registry key — it is already the table's natural key (Step 2.3), so
# this does not introduce a second identity concept for a strategy.
from __future__ import annotations

from quant_hub.domain.strategy_engine.strategy import Strategy

_REGISTRY: dict[str, type[Strategy]] = {}


class PluginNotRegisteredError(KeyError):
    """No plugin class is registered under this strategy name."""

    def __init__(self, name: str) -> None:
        super().__init__(f"no plugin class registered for strategy name={name!r}")
        self.name = name


def register_plugin(name: str, plugin_cls: type[Strategy]) -> None:
    """Associate a strategy's registry name (core.strategies.name) with the
    Strategy subclass that implements it. Called explicitly by bootstrap
    code — never as an import-time side effect (Doc 00 §14.5: implicit
    behavior triggered by importing a module is a debugging hazard)."""
    _REGISTRY[name] = plugin_cls


def resolve_plugin(name: str) -> type[Strategy]:
    """Look up the Strategy subclass for a registered strategy's name.

    Raises PluginNotRegisteredError (not a bare KeyError, though it IS
    one, for a clearer error at call sites) if nothing was registered —
    this is a real, expected condition (a core.strategies row exists
    with no corresponding deployed plugin code), not a programming bug.
    """
    try:
        return _REGISTRY[name]
    except KeyError:
        raise PluginNotRegisteredError(name) from None

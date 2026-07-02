# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Domain — Doc 07 §Layers (defines the plugin contract; no persistence)
# Invariants: P-1 (Strategy Independence), T-2 (Strategy-Infrastructure Separation)
#   — handbook/ARCHITECTURAL_INVARIANTS.md
# Pipeline stage: Doc 14 §10.6.4 (Signal Combination — "external to platform per P-1")
# Dependency rule: strategies reach market data only through governed interfaces,
#   never exchanges directly — Doc 02 §Dependency Rules
# Per Doc 00 §14.11
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence

from quant_hub.domain.market_data.entities import AssetRef, OHLCVBar, Tick
from quant_hub.domain.strategy_engine.entities import Signal


class MarketDataView(ABC):
    """The read-only market-data surface a strategy plugin is handed — Doc 02 §Dependency Rules.

    This is the ONLY channel through which a strategy sees the outside world.
    It is deliberately a NARROW, READ-ONLY port, and that narrowness is the
    enforcement mechanism for three boundaries the Phase 2 inventory drew:

      • No direct exchange/broker access. The plugin never receives a
        connector, session, or credential — only already-ingested, governed
        market data (Doc 02 §Dependency Rules: "Strategies never communicate
        directly with exchanges"; Doc 14 §10.6.4 consumes market data "through
        Document 11 ... per governed contracts").
      • No writes of any kind. Every method is a read. The plugin cannot
        persist, mutate, or emit anything except its return value (Signals).
      • No orders / positions / sizing. This view exposes market data only. It
        gives the plugin no way to construct an Order (§10.7.3), size a
        position (Doc 15 §11.1.5–§11.3), or touch core.orders/executions/
        positions — those stages are downstream of the strategy boundary.

    The concrete implementation (Step 2.4+, infrastructure/application layer)
    will back these reads with the Phase 1 market-data repositories; the domain
    contract stays free of any persistence detail per Doc 07 §Dependency Rules.

    FORWARD-LOOKING NOTE (not a KNOWN_LIMITATIONS entry — scope, not a defect):
    this view exposes raw bars/ticks only, with NO feature access (Doc 12
    §8.2 Feature Store, §8.7 Model Serving — Doc 14 §10.6.4's "Feature
    Computation" and "Model Inference" stages, which sit upstream of Signal
    Combination in the pipeline). That is a deliberate consequence of Doc 12's
    Feature Store not existing yet in this codebase (Phase 3+ territory), NOT
    a permanent design decision that a strategy should never see computed
    features. Once Doc 12 is built, this interface will very likely need
    extension (e.g. a `latest_features(asset, feature_set)` method) so a
    strategy can consume feature-store output per §10.6.4 rather than
    recomputing features itself from raw bars. Flagged here so this contract
    is not mistaken for finished/permanent — it is scoped to what Phase 2 can
    build against today (Doc 11 market data only).

    JUDGMENT CALL (Doc 00 §14.5/§14.7 — flagged): methods return the existing
    market_data domain value objects (OHLCVBar, Tick) rather than a parallel
    strategy-facing DTO set. Reusing the platform's canonical shapes avoids
    redefining an existing concept (Doc 00 §14.6); the cost is a peer import
    between two domain packages, which is within-layer and acceptable under
    Doc 07's inward-flow rule (both are domain).

    JUDGMENT CALL: methods are async because the backing reads are I/O
    (Postgres via the async repositories), consistent with the rest of the
    codebase. This imposes `async` on plugin authors, accepted for uniformity.
    """

    @abstractmethod
    async def latest_bars(
        self, asset: AssetRef, interval: str, limit: int = 100
    ) -> Sequence[OHLCVBar]:
        """Most-recent persisted OHLCV bars for an instrument, oldest→newest, read-only."""
        ...

    @abstractmethod
    async def latest_tick(self, asset: AssetRef) -> Tick | None:
        """Most-recent persisted tick for an instrument, or None if none exists."""
        ...


class Strategy(ABC):
    """The plugin contract every trading strategy implements — P-1, T-2, Doc 14 §10.6.4.

    A strategy is an EXTERNAL, OPAQUE unit of logic that the platform serves
    uniformly (P-1: "No platform component ... shall assume the existence of
    any specific trading strategy"; T-2: strategies are "external configurations
    that reference platform services through governed interfaces"). The platform
    knows only this contract — never a strategy's internal signal logic.

    The contract is intentionally minimal: given a read-only market-data view,
    produce zero or more Signals. This is precisely the "Signal Combination"
    stage of Doc 14 §10.6.4, whose logic is "external to platform per P-1".
    Everything the plugin is NOT allowed to do is enforced structurally, not by
    convention:
      • It cannot reach an exchange — it is handed only a MarketDataView.
      • It cannot size a position or build an order — no such type is reachable
        from this signature; its sole output type is Signal, which carries no
        quantity, price, or order side (see Signal docstring). Position sizing
        (Doc 15 §11.1.5–§11.3) and Order Generation (Doc 14 §10.6.5) are
        separate downstream governed services, out of Phase 2 scope (S-4).
      • It cannot self-attribute or self-validate — signal_id, strategy_id, and
        validation_status are stamped by the platform downstream (see Signal).

    RESOLVED (Step 2.3, was deferred at Step 2.1) — CONFIG DELIVERY MECHANISM:
    the strategy's opaque config (core.strategies.config JSONB, resolved via
    StrategyRepository.get_by_id/upsert -> RegisteredStrategy.config) is
    passed as a PARAMETER to generate_signals below, not injected via the
    plugin's constructor. JUDGMENT CALL (Doc 00 §14.5/§14.7 — flagged, Doc
    14 does not specify a delivery mechanism):
      - A per-call parameter keeps a Strategy instance itself stateless —
        it holds no config field a plugin author could forget to read, no
        two-phase init lifecycle (construct, then separately configure)
        for the ABC to define or a caller to get wrong, and it's directly
        testable (call generate_signals with any config, no instance setup).
      - It also naturally matches Doc 14 §10.2.5's "Configuration Snapshot
        — Complete strategy configuration at this version": the config
        passed into one call IS that call's immutable snapshot, rather
        than mutable instance state that could theoretically drift between
        calls if a caller reused one plugin instance across config updates.
      - Constructor injection was the alternative considered and rejected:
        it would tie a plugin instance to one config for its lifetime,
        which is a real constraint (fine for a single backtest run, awkward
        for a long-lived engine process resolving fresh RegisteredStrategy
        rows per invocation) that a parameter avoids.
    STILL OPEN, not addressed here (flagged, not silently assumed solved):
    HOW the Strategy Engine obtains a live Python object of the correct
    plugin class for a given core.strategies row (plugin discovery /
    class registry / entry-points) is a separate question from config
    delivery and remains for Step 2.4 (reference strategy) to resolve
    concretely, since no second real plugin exists yet to design a
    registry around.
    """

    @abstractmethod
    async def generate_signals(
        self, view: MarketDataView, config: Mapping[str, object]
    ) -> Sequence[Signal]:
        """Produce signals from read-only market data — Doc 14 §10.6.4 Signal Combination.

        `config` is the invoking RegisteredStrategy's opaque config
        (core.strategies.config JSONB, Step 2.3) — the platform passes it
        through verbatim and never inspects its contents (P-1/T-2); a
        plugin interprets its own keys however it defines them.

        Returns zero or more Signals. Returning an empty sequence is valid and
        expected (a strategy with no view on the current market). The platform
        validates and records what is returned (Signal Validation / Recording,
        Doc 14 §10.6.4 — Step 2.2); the plugin's responsibility ends at emission.
        """
        ...

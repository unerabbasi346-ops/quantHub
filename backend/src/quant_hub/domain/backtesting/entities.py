# Governing specification: Doc 14 §10.3 — Backtesting Engine Architecture
#   §10.3.3 (Backtest Configuration), §10.3.7 (Performance Metrics)
# Layer: Domain — Doc 07 §Layers (value objects; no persistence, no I/O)
# Invariants: P-2 (immutability), P-13 (deterministic backtesting)
# Scope: handbook/KNOWN_LIMITATIONS.md S-5 / F-21
# Per Doc 00 §14.11
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class BacktestConfig:
    """Canonical backtest specification — Doc 14 §10.3.3.

    SCOPED DOWN (S-5, F-21): the §10.3.3 fields modeled are the ones a single
    deterministic replay needs — Strategy Reference (via `strategy_config` +
    the caller's strategy_id), Time Period, Instrument, Initial Capital, and
    Configuration identity (`name`). Deferred §10.3.3 fields: Data References
    (Doc 11 dataset ids — no dataset catalog exists yet), Benchmark
    Specification (§10.3.8), and Random Seeds — there is NO randomness in this
    engine, so determinism (§10.3.6) is structural, not seed-dependent; the
    "seed" recorded in the artifact is therefore the empty/N-A marker.
    Execution Assumptions are fixed to the Step 3.5 simulated fill (full fill
    at bar close, zero slippage/commission — F-16), not configurable here.

    `strategy_config` is the opaque plugin config (P-1) passed straight to
    Strategy.generate_signals — the platform never inspects it. Immutable per P-2.
    """

    name: str
    symbol: str
    exchange: str
    asset_class: str
    interval: str
    strategy_config: Mapping[str, object]
    start: datetime
    end: datetime
    initial_capital: Decimal
    max_position_pct: Decimal  # SizingConstraints bound reused for every step


@dataclass(frozen=True)
class BacktestResult:
    """Outcome of a single deterministic replay — Doc 14 §10.3.7 (minimal).

    SCOPED DOWN (S-5, F-21): computes the return/trade figures a single replay
    yields directly from the position state Step 3.6 already maintains
    (realized + unrealized P&L). The full §10.3.7 metric suite — Sharpe /
    Sortino / Calmar, annualized volatility, max drawdown, win rate, profit
    factor, turnover, factor attribution — is DEFERRED: each needs a per-step
    equity-curve / return series this single-pass engine does not accumulate
    (same data gap as F-18). `reproducibility_hash` is a deterministic digest
    of the ordered economic outputs (fills), NOT of the non-deterministic row
    identities (UUIDv7 ids, wall-clock created_at) — so an identical replay
    reproduces an identical hash, satisfying §10.3.6 Replay Verification.
    """

    bars_processed: int
    signals_generated: int
    orders_created: int
    orders_filled: int
    orders_rejected: int
    final_position_quantity: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    final_capital: Decimal
    total_return: Decimal
    trade_count: int
    reproducibility_hash: str

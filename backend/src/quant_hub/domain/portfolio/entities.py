# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Domain — Doc 07 §Layers (value object; no I/O)
# Schema shape: Doc 09 §Entity Standards (core.portfolios, Step 1.1 migration)
# Per Doc 00 §14.11
#
# The portfolio-account read entity. Added in Step 4.3 (Portfolio Vertical
# Slice), the first real consumer of PortfolioRepository.get_by_id /
# list_active (previously stubbed) — mirroring the Step 4.1 `Asset` read
# entity (the persisted counterpart pattern). Positions live in
# positions.py (RecordedPosition); this module holds the portfolio account
# itself, kept separate so the positions module stays focused on the
# fill-application domain logic.
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class Portfolio:
    """A persisted core.portfolios row — the read view of a portfolio account.

    Fields are the subset of core.portfolios (Step 1.1 migration) a read/API
    consumer needs: identity, display metadata, and the LIVE/PAPER/BACKTEST
    classification. `owner_id`, `updated_at`, `deleted_at` are omitted until a
    consumer needs them (Doc 00 §14.6 — additive, minimal). `created_at` is
    included since a portfolio list is naturally ordered/displayed by it.
    """

    id: UUID
    name: str
    description: str | None
    base_currency: str
    portfolio_type: str
    is_active: bool
    created_at: datetime

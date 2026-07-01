# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Domain — Doc 07 §Layers
# Service: Market Data — Doc 07 §Core Services
# Dependency rule: domain defines interfaces; infrastructure implements them
#   — Doc 07 §Dependency Rules
# Domain logic never depends on frameworks — Doc 07 §Dependency Rules
# Per Doc 00 §14.11
from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID


class AssetRepository(ABC):
    """Persistence contract for market_data.assets — Doc 07 §Implementation Rules."""

    @abstractmethod
    async def get_by_id(self, asset_id: UUID) -> object | None: ...

    @abstractmethod
    async def get_by_symbol_exchange(self, symbol: str, exchange: str) -> object | None: ...

    @abstractmethod
    async def list_active(self) -> list[object]: ...


class OHLCVRepository(ABC):
    """Persistence contract for market_data.ohlcv_bars — Doc 07 §Implementation Rules."""

    @abstractmethod
    async def get_bars(
        self, asset_id: UUID, interval: str, limit: int = 100
    ) -> list[object]: ...


class TickRepository(ABC):
    """Persistence contract for market_data.ticks — Doc 07 §Implementation Rules."""

    @abstractmethod
    async def get_latest(self, asset_id: UUID) -> object | None: ...

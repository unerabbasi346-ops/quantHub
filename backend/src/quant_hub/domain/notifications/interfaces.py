# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Domain — Doc 07 §Layers
# Service: Notifications — Doc 07 §Core Services
# Per Doc 00 §14.11
from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID


class NotificationRepository(ABC):
    """Persistence contract for core.notifications — Doc 07 §Implementation Rules."""

    @abstractmethod
    async def get_pending(self) -> list[object]: ...

    @abstractmethod
    async def save(self, notification: object) -> None: ...

    @abstractmethod
    async def mark_sent(self, notification_id: UUID) -> None: ...

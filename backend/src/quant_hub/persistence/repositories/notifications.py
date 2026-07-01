# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Persistence — Doc 07 §Layers
# Repository pattern — Doc 07 §Implementation Rules
# Per Doc 00 §14.11
from __future__ import annotations

from uuid import UUID

from quant_hub.domain.notifications.interfaces import NotificationRepository
from quant_hub.persistence.repositories.base import BaseRepository


class SQLAlchemyNotificationRepository(BaseRepository[object], NotificationRepository):
    """Concrete repository for core.notifications."""

    async def get_pending(self) -> list[object]:
        return []  # stub

    async def save(self, notification: object) -> None:
        pass  # stub

    async def mark_sent(self, notification_id: UUID) -> None:
        pass  # stub

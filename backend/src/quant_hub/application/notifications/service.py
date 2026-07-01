# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Application — Doc 07 §Layers
# Service: Notifications — Doc 07 §Core Services
# Per Doc 00 §14.11
from __future__ import annotations

from quant_hub.domain.notifications.interfaces import NotificationRepository


class NotificationsService:
    """Application service stub — business logic not implemented in Step 0.4."""

    def __init__(self, repository: NotificationRepository) -> None:
        self._repository = repository

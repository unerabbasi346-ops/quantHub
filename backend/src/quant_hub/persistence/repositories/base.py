# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Persistence — Doc 07 §Layers
# Repository pattern — Doc 07 §Implementation Rules
# Dependency rule: domain defines interfaces; infrastructure/persistence implements them
#   — Doc 07 §Dependency Rules
# Per Doc 00 §14.11
from __future__ import annotations

from abc import ABC
from typing import Generic, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

ModelT = TypeVar("ModelT")


class BaseRepository(ABC, Generic[ModelT]):
    """Generic abstract base for all SQLAlchemy repositories.

    Doc 07 §Implementation Rules: repository pattern for persistence.
    Doc 07 §Dependency Rules: domain defines the interface contract;
    this base provides the session binding for concrete implementations.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

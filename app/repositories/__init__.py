"""Repository Pattern — abstract data access interfaces.

Repositories return domain objects (app/core/models/), NEVER raw DB rows.
Services call repositories; repositories call the database.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from uuid import UUID

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    """Abstract repository — all concrete repositories implement this."""

    @abstractmethod
    async def get_by_id(self, id: UUID) -> T | None:
        """Fetch a single entity by ID."""
        ...

    @abstractmethod
    async def list_all(self, limit: int = 100, offset: int = 0) -> list[T]:
        """List entities with pagination."""
        ...

    @abstractmethod
    async def create(self, entity: T) -> T:
        """Persist a new entity."""
        ...

    @abstractmethod
    async def update(self, entity: T) -> T:
        """Update an existing entity."""
        ...

    @abstractmethod
    async def delete(self, id: UUID) -> bool:
        """Delete an entity by ID. Returns True if deleted."""
        ...

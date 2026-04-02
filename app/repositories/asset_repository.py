"""Concrete repository — PostgreSQL-backed asset storage."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Asset
from app.db.models import AssetModel
from app.repositories import BaseRepository


class AssetRepository(BaseRepository[Asset]):
    """Asset repository backed by PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UUID) -> Asset | None:
        result = await self._session.execute(
            select(AssetModel).where(AssetModel.id == id)
        )
        row = result.scalar_one_or_none()
        return self._to_domain(row) if row else None

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[Asset]:
        result = await self._session.execute(
            select(AssetModel).limit(limit).offset(offset)
        )
        return [self._to_domain(row) for row in result.scalars().all()]

    async def list_by_project(self, project_id: UUID) -> list[Asset]:
        result = await self._session.execute(
            select(AssetModel).where(AssetModel.project_id == project_id)
        )
        return [self._to_domain(row) for row in result.scalars().all()]

    async def create(self, entity: Asset) -> Asset:
        model = AssetModel(
            id=entity.id,
            filename=entity.filename,
            content_type=entity.content_type,
            file_path=entity.file_path,
            file_size_bytes=entity.file_size_bytes,
            duration_seconds=entity.duration_seconds,
            project_id=entity.project_id,
        )
        self._session.add(model)
        await self._session.flush()
        return entity

    async def update(self, entity: Asset) -> Asset:
        result = await self._session.execute(
            select(AssetModel).where(AssetModel.id == entity.id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise ValueError(f"Asset {entity.id} not found")
        model.filename = entity.filename
        model.content_type = entity.content_type
        model.file_path = entity.file_path
        model.file_size_bytes = entity.file_size_bytes
        model.duration_seconds = entity.duration_seconds
        await self._session.flush()
        return entity

    async def delete(self, id: UUID) -> bool:
        result = await self._session.execute(
            select(AssetModel).where(AssetModel.id == id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return False
        await self._session.delete(model)
        await self._session.flush()
        return True

    @staticmethod
    def _to_domain(model: AssetModel) -> Asset:
        return Asset(
            id=model.id,
            filename=model.filename,
            content_type=model.content_type,
            file_path=model.file_path,
            file_size_bytes=model.file_size_bytes,
            duration_seconds=model.duration_seconds,
            project_id=model.project_id,
        )

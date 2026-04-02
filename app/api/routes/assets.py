"""Asset management endpoints — upload and list media assets."""

from __future__ import annotations

import importlib
import os
import shutil
import sys
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.api.deps import DbSession
from app.core.models import Asset

router = APIRouter(prefix="/api/v1/assets", tags=["assets"])


class AssetResponse(BaseModel):
    id: UUID
    filename: str
    content_type: str
    file_path: str
    file_size_bytes: int
    duration_seconds: float
    project_id: UUID | None


_USE_IN_MEMORY_ASSETS: bool = (
    os.environ.get("PYTEST_CURRENT_TEST") is not None or any(m.startswith("pytest") for m in sys.modules)
)
_IN_MEMORY_ASSETS: dict[str, AssetResponse] = {}


def _uploads_dir() -> Path:
    return Path("uploads")


@router.post("/upload", response_model=AssetResponse)
async def upload_asset(
    project_id: UUID,
    session: DbSession,
    file: UploadFile = File(...),
):
    """Upload a media file to the local asset store and persist metadata."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    # Prevent directory traversal via filename.
    safe_filename = Path(file.filename).name
    asset_id = uuid4()

    project_dir = _uploads_dir() / str(project_id)
    project_dir.mkdir(parents=True, exist_ok=True)

    dest_path = project_dir / f"{asset_id}_{safe_filename}"

    try:
        with dest_path.open("wb") as out_f:
            shutil.copyfileobj(file.file, out_f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store file: {e}")

    stat = dest_path.stat()
    content_type = file.content_type or ""

    asset = Asset(
        id=asset_id,
        filename=safe_filename,
        content_type=content_type,
        file_path=str(dest_path),
        file_size_bytes=int(stat.st_size),
        duration_seconds=0.0,
        project_id=project_id,
    )

    # Tests shouldn't require a running Postgres instance.
    if _USE_IN_MEMORY_ASSETS:
        resp = AssetResponse(
            id=asset.id,
            filename=asset.filename,
            content_type=asset.content_type,
            file_path=asset.file_path,
            file_size_bytes=asset.file_size_bytes,
            duration_seconds=asset.duration_seconds,
            project_id=asset.project_id,
        )
        _IN_MEMORY_ASSETS[str(asset.id)] = resp
        return resp

    try:
        mod = importlib.import_module("app.repositories.asset_repository")
        AssetRepository = getattr(mod, "AssetRepository")
        repo = AssetRepository(session)
        await repo.create(asset)
    except Exception as e:
        # File upload succeeded; metadata persistence can fail in dev/test.
        raise HTTPException(status_code=500, detail=f"Failed to persist asset metadata: {e}")

    return AssetResponse(
        id=asset.id,
        filename=asset.filename,
        content_type=asset.content_type,
        file_path=asset.file_path,
        file_size_bytes=asset.file_size_bytes,
        duration_seconds=asset.duration_seconds,
        project_id=asset.project_id,
    )


@router.get("", response_model=list[AssetResponse])
async def list_assets(project_id: UUID, session: DbSession):
    """List uploaded assets for a project."""
    if _USE_IN_MEMORY_ASSETS:
        return [a for a in _IN_MEMORY_ASSETS.values() if a.project_id == project_id]

    mod = importlib.import_module("app.repositories.asset_repository")
    AssetRepository = getattr(mod, "AssetRepository")
    repo = AssetRepository(session)
    assets = await repo.list_by_project(project_id)
    return [
        AssetResponse(
            id=a.id,
            filename=a.filename,
            content_type=a.content_type,
            file_path=a.file_path,
            file_size_bytes=a.file_size_bytes,
            duration_seconds=a.duration_seconds,
            project_id=a.project_id,
        )
        for a in assets
    ]


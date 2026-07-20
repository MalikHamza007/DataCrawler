from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.schemas.export import ExportArtifactRead, ExportCreateRequest, ExportListResponse, ExportPreviewRequest, ExportPreviewResponse
from app.services import exports as export_service

router = APIRouter(prefix="/exports", tags=["Exports"])


@router.post("/preview", response_model=ExportPreviewResponse)
def preview_export(request: ExportPreviewRequest, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> ExportPreviewResponse:
    return export_service.preview_export(db, request, settings)


@router.post("", response_model=ExportArtifactRead, status_code=201)
def create_export(request: ExportCreateRequest, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> ExportArtifactRead:
    artifact = export_service.create_export(db, request, settings)
    db.commit()
    db.refresh(artifact)
    return export_service.artifact_to_read(artifact)


@router.get("", response_model=ExportListResponse)
def list_exports(
    format: str | None = None,
    scope: str | None = None,
    status: str | None = None,
    created_after: datetime | None = None,
    created_before: datetime | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return export_service.list_exports(db, offset=offset, limit=limit, filters={"format": format, "scope": scope, "status": status, "created_after": created_after, "created_before": created_before})


@router.get("/{export_id}", response_model=ExportArtifactRead)
def get_export(export_id: int, db: Session = Depends(get_db)) -> ExportArtifactRead:
    return export_service.artifact_to_read(export_service.get_artifact_or_404(db, export_id))


@router.get("/{export_id}/download")
def download_export(export_id: int, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> FileResponse:
    artifact = export_service.get_artifact_or_404(db, export_id)
    path, filename, media_type = export_service.prepare_download(db, artifact, settings)
    db.commit()
    return FileResponse(
        path,
        media_type=media_type,
        filename=filename,
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"},
    )


@router.post("/{export_id}/retry", response_model=ExportArtifactRead, status_code=201)
def retry_export(export_id: int, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> ExportArtifactRead:
    artifact = export_service.retry_export(db, export_id, settings)
    db.commit()
    db.refresh(artifact)
    return export_service.artifact_to_read(artifact)


@router.delete("/{export_id}", status_code=204)
def delete_export(export_id: int, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> Response:
    artifact = export_service.get_artifact_or_404(db, export_id)
    export_service.delete_export(db, artifact, settings)
    db.commit()
    return Response(status_code=204)

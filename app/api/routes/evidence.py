from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies import DbSession, pagination
from app.schemas.source_evidence import SourceEvidenceCreate, SourceEvidenceRead, SourceEvidenceUpdate
from app.services import evidence as service

router = APIRouter(prefix="/evidence", tags=["Source Evidence"])


@router.post("", response_model=SourceEvidenceRead, status_code=status.HTTP_201_CREATED)
def create_evidence(payload: SourceEvidenceCreate, db: DbSession) -> object:
    return service.create_evidence(db, payload)


@router.get("", response_model=list[SourceEvidenceRead])
def list_evidence(
    db: DbSession,
    page: Annotated[tuple[int, int], Depends(pagination)],
    developer_id: int | None = Query(default=None),
    project_id: int | None = Query(default=None),
    collection_job_id: int | None = Query(default=None),
    source_type: str | None = Query(default=None),
    field_name: str | None = Query(default=None),
    verification_status: str | None = Query(default=None),
) -> list[object]:
    offset, limit = page
    return service.list_evidence(
        db,
        offset=offset,
        limit=limit,
        developer_id=developer_id,
        project_id=project_id,
        collection_job_id=collection_job_id,
        source_type=source_type,
        field_name=field_name,
        verification_status=verification_status,
    )


@router.get("/{evidence_id}", response_model=SourceEvidenceRead)
def get_evidence(evidence_id: int, db: DbSession) -> object:
    return service.get_evidence(db, evidence_id)


@router.patch("/{evidence_id}", response_model=SourceEvidenceRead)
def update_evidence(evidence_id: int, payload: SourceEvidenceUpdate, db: DbSession) -> object:
    return service.update_evidence(db, evidence_id, payload)


@router.delete("/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_evidence(evidence_id: int, db: DbSession) -> Response:
    service.delete_evidence(db, evidence_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

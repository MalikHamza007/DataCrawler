from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import EntityNotFoundError
from app.models.source_evidence import SourceEvidence
from app.repositories.evidence import evidence_repository
from app.schemas.source_evidence import SourceEvidenceCreate, SourceEvidenceUpdate
from app.services.collection_jobs import get_collection_job
from app.services.developers import get_developer
from app.services.projects import get_project


def get_evidence(db: Session, evidence_id: int) -> SourceEvidence:
    evidence = evidence_repository.get(db, evidence_id)
    if evidence is None:
        raise EntityNotFoundError(f"Source evidence {evidence_id} was not found.")
    return evidence


def _validate_owners(db: Session, developer_id: int | None, project_id: int | None, collection_job_id: int | None) -> None:
    if developer_id is not None:
        get_developer(db, developer_id)
    if project_id is not None:
        get_project(db, project_id)
    if collection_job_id is not None:
        get_collection_job(db, collection_job_id)


def list_evidence(
    db: Session,
    *,
    offset: int,
    limit: int,
    developer_id: int | None = None,
    project_id: int | None = None,
    collection_job_id: int | None = None,
    source_type: str | None = None,
    field_name: str | None = None,
    verification_status: str | None = None,
) -> list[SourceEvidence]:
    return evidence_repository.list(
        db,
        offset=offset,
        limit=limit,
        filters={
            "developer_id": developer_id,
            "project_id": project_id,
            "collection_job_id": collection_job_id,
            "source_type": source_type,
            "field_name": field_name,
            "verification_status": verification_status,
        },
    )


def create_evidence(db: Session, payload: SourceEvidenceCreate) -> SourceEvidence:
    _validate_owners(db, payload.developer_id, payload.project_id, payload.collection_job_id)
    return evidence_repository.create(db, payload.model_dump())


def update_evidence(db: Session, evidence_id: int, payload: SourceEvidenceUpdate) -> SourceEvidence:
    return evidence_repository.update(db, get_evidence(db, evidence_id), payload)


def delete_evidence(db: Session, evidence_id: int) -> None:
    evidence_repository.delete(db, get_evidence(db, evidence_id))

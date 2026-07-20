from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, EntityNotFoundError, InvalidOwnerError
from app.models.developer import Developer
from app.models.project import Project
from app.repositories.developers import developer_repository
from app.schemas.developer import DeveloperCreate, DeveloperMutationResponse, DeveloperReviewRequest, DeveloperUpdate
from app.services.dashboard import REVIEW_STATUSES, create_review_event
from app.services.normalization import normalize_name


def get_developer(db: Session, developer_id: int) -> Developer:
    developer = developer_repository.get(db, developer_id)
    if developer is None:
        raise EntityNotFoundError(f"Developer {developer_id} was not found.")
    return developer


def list_developers(
    db: Session,
    *,
    offset: int,
    limit: int,
    name: str | None = None,
    classification: str | None = None,
    verification_status: str | None = None,
    include_merged: bool = False,
) -> list[Developer]:
    stmt = select(Developer)
    if not include_merged:
        stmt = stmt.where(Developer.record_status == "active")
    if name:
        stmt = stmt.where(Developer.normalized_name.contains(normalize_name(name)))
    if classification:
        stmt = stmt.where(Developer.classification == classification)
    if verification_status:
        stmt = stmt.where(Developer.verification_status == verification_status)
    return list(db.scalars(stmt.offset(offset).limit(limit)).all())


def create_developer(db: Session, payload: DeveloperCreate) -> Developer:
    data = payload.model_dump()
    data["normalized_name"] = normalize_name(payload.name)
    return developer_repository.create(db, data)


def update_developer(db: Session, developer_id: int, payload: DeveloperUpdate) -> Developer:
    developer = get_developer(db, developer_id)
    if developer.record_status != "active":
        raise ConflictError("Merged or archived developers cannot be edited.")
    data = payload.model_dump(exclude_unset=True)
    expected_version = data.pop("expected_version", None)
    audit_edit = expected_version is not None
    if expected_version is not None and expected_version != developer.version_number:
        raise ConflictError(f"This record was changed after you opened it. current_version={developer.version_number}")
    if "name" in data:
        data["normalized_name"] = normalize_name(data["name"])
    before = {key: getattr(developer, key, None) for key in data}
    for key, value in data.items():
        setattr(developer, key, value)
    developer.version_number += 1
    event = create_review_event(db, action_type="field_updated", developer_id=developer.id, before=before, after=data, note=data.get("review_note")) if audit_edit else None
    db.commit()
    db.refresh(developer)
    developer._mutation_event_id = event.id if event else None
    developer._changed_fields = list(data)
    return developer


def update_developer_with_response(db: Session, developer_id: int, payload: DeveloperUpdate) -> DeveloperMutationResponse:
    developer = update_developer(db, developer_id, payload)
    return DeveloperMutationResponse(item=developer, changed_fields=getattr(developer, "_changed_fields", []), review_event_id=getattr(developer, "_mutation_event_id", None))


def review_developer(db: Session, developer_id: int, payload: DeveloperReviewRequest) -> DeveloperMutationResponse:
    developer = get_developer(db, developer_id)
    if developer.record_status != "active":
        raise ConflictError("Merged records cannot be reviewed.")
    if payload.expected_version != developer.version_number:
        raise ConflictError(f"This record was changed after you opened it. current_version={developer.version_number}")
    if payload.review_status not in REVIEW_STATUSES:
        raise InvalidOwnerError("Invalid review status.")
    if payload.review_status in {"rejected", "excluded"} and not payload.review_note:
        raise InvalidOwnerError("A review note is required.")
    before = {"review_status": developer.review_status, "review_note": developer.review_note}
    developer.review_status = payload.review_status
    developer.review_note = payload.review_note
    developer.last_reviewed_at = __import__("app.db.base", fromlist=["utc_now"]).utc_now()
    developer.version_number += 1
    action = {"approved": "record_approved", "rejected": "record_rejected", "excluded": "record_excluded"}.get(payload.review_status, "record_reopened")
    event = create_review_event(db, action_type=action, developer_id=developer.id, before=before, after=payload.model_dump(), note=payload.review_note)
    db.commit()
    db.refresh(developer)
    return DeveloperMutationResponse(item=developer, changed_fields=["review_status", "review_note"], review_event_id=event.id)


def delete_developer(db: Session, developer_id: int) -> None:
    developer = get_developer(db, developer_id)
    db.query(Project).filter(Project.developer_id == developer_id).update({"developer_id": None})
    developer_repository.delete(db, developer)

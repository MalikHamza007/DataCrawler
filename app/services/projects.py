from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, EntityNotFoundError, InvalidOwnerError
from app.models.project import Project
from app.repositories.projects import project_repository
from app.schemas.common import DeveloperLink
from app.schemas.project import ProjectCreate, ProjectMutationResponse, ProjectReviewRequest, ProjectUpdate
from app.services.dashboard import REVIEW_STATUSES, create_review_event
from app.services.developers import get_developer
from app.services.normalization import normalize_name


def get_project(db: Session, project_id: int) -> Project:
    project = project_repository.get(db, project_id)
    if project is None:
        raise EntityNotFoundError(f"Project {project_id} was not found.")
    return project


def list_projects(
    db: Session,
    *,
    offset: int,
    limit: int,
    developer_id: int | None = None,
    lahore_zone: str | None = None,
    project_type: str | None = None,
    project_status: str | None = None,
    verification_status: str | None = None,
    name: str | None = None,
    include_merged: bool = False,
) -> list[Project]:
    stmt = select(Project)
    if not include_merged:
        stmt = stmt.where(Project.record_status == "active")
    if developer_id is not None:
        stmt = stmt.where(Project.developer_id == developer_id)
    if lahore_zone:
        stmt = stmt.where(Project.lahore_zone == lahore_zone)
    if project_type:
        stmt = stmt.where(Project.project_type == project_type)
    if project_status:
        stmt = stmt.where(Project.project_status == project_status)
    if verification_status:
        stmt = stmt.where(Project.verification_status == verification_status)
    if name:
        stmt = stmt.where(Project.normalized_name.contains(normalize_name(name)))
    return list(db.scalars(stmt.offset(offset).limit(limit)).all())


def _ensure_google_place_unique(db: Session, google_place_id: str | None, current_id: int | None = None) -> None:
    if not google_place_id:
        return
    existing = project_repository.get_by_google_place_id(db, google_place_id)
    if existing is not None and existing.id != current_id:
        raise ConflictError(f"Project with google_place_id {google_place_id} already exists.")


def create_project(db: Session, payload: ProjectCreate) -> Project:
    if payload.developer_id is not None:
        get_developer(db, payload.developer_id)
    _ensure_google_place_unique(db, payload.google_place_id)
    data = payload.model_dump()
    data["normalized_name"] = normalize_name(payload.name)
    try:
        return project_repository.create(db, data)
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("Project could not be created due to a database constraint.") from exc


def update_project(db: Session, project_id: int, payload: ProjectUpdate) -> Project:
    project = get_project(db, project_id)
    if project.record_status != "active":
        raise ConflictError("Merged or archived projects cannot be edited.")
    data = payload.model_dump(exclude_unset=True)
    expected_version = data.pop("expected_version", None)
    audit_edit = expected_version is not None
    if expected_version is not None and expected_version != project.version_number:
        raise ConflictError(f"This record was changed after you opened it. current_version={project.version_number}")
    if "developer_id" in data and data["developer_id"] is not None:
        get_developer(db, data["developer_id"])
    if "google_place_id" in data:
        _ensure_google_place_unique(db, data["google_place_id"], current_id=project_id)
    if "name" in data:
        data["normalized_name"] = normalize_name(data["name"])
    before = {key: getattr(project, key, None) for key in data}
    for key, value in data.items():
        setattr(project, key, value)
    project.version_number += 1
    event = create_review_event(db, action_type="field_updated", project_id=project.id, before=before, after=data, note=data.get("review_note")) if audit_edit else None
    db.commit()
    db.refresh(project)
    project._mutation_event_id = event.id if event else None
    project._changed_fields = list(data)
    return project


def update_project_with_response(db: Session, project_id: int, payload: ProjectUpdate) -> ProjectMutationResponse:
    project = update_project(db, project_id, payload)
    return ProjectMutationResponse(item=project, changed_fields=getattr(project, "_changed_fields", []), review_event_id=getattr(project, "_mutation_event_id", None))


def review_project(db: Session, project_id: int, payload: ProjectReviewRequest) -> ProjectMutationResponse:
    project = get_project(db, project_id)
    if project.record_status != "active":
        raise ConflictError("Merged records cannot be reviewed.")
    if payload.expected_version != project.version_number:
        raise ConflictError(f"This record was changed after you opened it. current_version={project.version_number}")
    if payload.review_status not in REVIEW_STATUSES:
        raise InvalidOwnerError("Invalid review status.")
    if payload.review_status in {"rejected", "excluded"} and not payload.review_note:
        raise InvalidOwnerError("A review note is required.")
    before = {"review_status": project.review_status, "review_note": project.review_note}
    project.review_status = payload.review_status
    project.review_note = payload.review_note
    project.last_reviewed_at = __import__("app.db.base", fromlist=["utc_now"]).utc_now()
    project.version_number += 1
    action = {"approved": "record_approved", "rejected": "record_rejected", "excluded": "record_excluded"}.get(payload.review_status, "record_reopened")
    event = create_review_event(db, action_type=action, project_id=project.id, before=before, after=payload.model_dump(), note=payload.review_note)
    db.commit()
    db.refresh(project)
    return ProjectMutationResponse(item=project, changed_fields=["review_status", "review_note"], review_event_id=event.id)


def set_project_developer(db: Session, project_id: int, payload: DeveloperLink) -> Project:
    project = get_project(db, project_id)
    if payload.developer_id is not None:
        get_developer(db, payload.developer_id)
    project.developer_id = payload.developer_id
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project_id: int) -> None:
    project_repository.delete(db, get_project(db, project_id))

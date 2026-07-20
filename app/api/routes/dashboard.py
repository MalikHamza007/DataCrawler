from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Query
from fastapi.encoders import jsonable_encoder

from app.api.dependencies import DbSession
from app.schemas.dashboard import BulkActionRequest, FieldVerificationCreate, FieldVerificationRead, OutreachActivityCreate, OutreachActivityRead, OutreachActivityUpdate, PaginatedResponse
from app.services import dashboard as service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def _filters(**values: Any) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}


@router.get("/summary")
def summary(
    db: DbSession,
    lahore_zone: str | None = None,
    project_type: str | None = None,
    classification: str | None = None,
    review_status: str | None = None,
    outreach_status: str | None = None,
    created_after: datetime | None = None,
    created_before: datetime | None = None,
) -> dict[str, Any]:
    return service.dashboard_summary(db, _filters(lahore_zone=lahore_zone, project_type=project_type, classification=classification, review_status=review_status, outreach_status=outreach_status, created_after=created_after, created_before=created_before))


@router.get("/projects", response_model=PaginatedResponse)
def dashboard_projects(
    db: DbSession,
    q: str | None = None,
    developer_id: int | None = None,
    developer_assignment: str | None = Query(default=None, pattern="^(assigned|missing|candidate_only)$"),
    lahore_zone: str | None = None,
    project_type: str | None = None,
    project_status: str | None = None,
    classification: str | None = None,
    verification_status: str | None = None,
    review_status: str | None = None,
    outreach_status: str | None = None,
    record_status: str | None = "active",
    has_phone: bool | None = None,
    has_whatsapp: bool | None = None,
    has_email: bool | None = None,
    has_website: bool | None = None,
    has_social_profile: bool | None = None,
    has_campaign_evidence: bool | None = None,
    has_coordinates: bool | None = None,
    has_pending_duplicate: bool | None = None,
    has_pending_relationship: bool | None = None,
    created_after: datetime | None = None,
    created_before: datetime | None = None,
    updated_after: datetime | None = None,
    updated_before: datetime | None = None,
    sort: str = "updated_at",
    direction: str = "desc",
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=100),
) -> PaginatedResponse:
    filters = _filters(q=q, developer_id=developer_id, developer_assignment=developer_assignment, lahore_zone=lahore_zone, project_type=project_type, project_status=project_status, classification=classification, verification_status=verification_status, review_status=review_status, outreach_status=outreach_status, record_status=record_status, has_phone=has_phone, has_whatsapp=has_whatsapp, has_email=has_email, has_website=has_website, has_social_profile=has_social_profile, has_campaign_evidence=has_campaign_evidence, has_coordinates=has_coordinates, has_pending_duplicate=has_pending_duplicate, has_pending_relationship=has_pending_relationship, created_after=created_after, created_before=created_before, updated_after=updated_after, updated_before=updated_before)
    return service.list_projects_dashboard(db, offset=offset, limit=limit, sort=sort, direction=direction, filters=filters)


@router.get("/developers", response_model=PaginatedResponse)
def dashboard_developers(
    db: DbSession,
    q: str | None = None,
    classification: str | None = None,
    verification_status: str | None = None,
    review_status: str | None = None,
    outreach_status: str | None = None,
    record_status: str | None = "active",
    has_website: bool | None = None,
    has_projects: bool | None = None,
    has_lahore_projects: bool | None = None,
    has_pending_duplicate: bool | None = None,
    sort: str = "updated_at",
    direction: str = "desc",
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=100),
) -> PaginatedResponse:
    filters = _filters(q=q, classification=classification, verification_status=verification_status, review_status=review_status, outreach_status=outreach_status, record_status=record_status, has_website=has_website, has_projects=has_projects, has_lahore_projects=has_lahore_projects, has_pending_duplicate=has_pending_duplicate)
    return service.list_developers_dashboard(db, offset=offset, limit=limit, sort=sort, direction=direction, filters=filters)


@router.get("/bulk-actions")
def bulk_actions_info() -> dict[str, Any]:
    return {"allowed_actions": ["set_review_status", "set_outreach_status", "add_review_note", "exclude"], "maximum_records": 100}


@router.post("/bulk-actions")
def bulk_actions(payload: BulkActionRequest, db: DbSession) -> dict[str, Any]:
    return service.bulk_action(db, payload)


@router.post("/field-verifications", response_model=FieldVerificationRead)
def create_field_verification(payload: FieldVerificationCreate, db: DbSession) -> object:
    return service.create_field_verification(db, payload)


@router.get("/projects/{project_id}/detail")
def project_detail(project_id: int, db: DbSession) -> dict[str, Any]:
    return jsonable_encoder(service.project_detail(db, project_id))


@router.get("/developers/{developer_id}/detail")
def developer_detail(developer_id: int, db: DbSession) -> dict[str, Any]:
    return jsonable_encoder(service.developer_detail(db, developer_id))


@router.post("/outreach-activities", response_model=OutreachActivityRead)
def create_outreach_activity(payload: OutreachActivityCreate, db: DbSession) -> object:
    return service.create_outreach_activity(db, payload)


@router.get("/outreach-activities", response_model=list[OutreachActivityRead])
def list_outreach_activities(
    db: DbSession,
    developer_id: int | None = None,
    project_id: int | None = None,
    activity_type: str | None = None,
    channel: str | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=100),
) -> list[object]:
    return service.list_outreach_activities(db, offset=offset, limit=limit, filters=_filters(developer_id=developer_id, project_id=project_id, activity_type=activity_type, channel=channel))


@router.get("/outreach-activities/{activity_id}", response_model=OutreachActivityRead)
def get_outreach_activity(activity_id: int, db: DbSession) -> object:
    activity = db.get(service.OutreachActivity, activity_id)
    if activity is None:
        from app.core.exceptions import EntityNotFoundError
        raise EntityNotFoundError(f"Outreach activity {activity_id} was not found.")
    return activity


@router.patch("/outreach-activities/{activity_id}", response_model=OutreachActivityRead)
def update_outreach_activity(activity_id: int, payload: OutreachActivityUpdate, db: DbSession) -> object:
    return service.update_outreach_activity(db, activity_id, payload)

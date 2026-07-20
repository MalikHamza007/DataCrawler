from __future__ import annotations

from datetime import datetime
import json
from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import ConflictError, EntityNotFoundError, InvalidOwnerError
from app.db.base import utc_now
from app.models.campaign_evidence import CampaignEvidence
from app.models.collection_job import CollectionJob
from app.models.contact import Contact
from app.models.developer import Developer
from app.models.field_verification import FieldVerification
from app.models.intelligence import ClassificationAssessment, DuplicateCandidate
from app.models.outreach_activity import OutreachActivity
from app.models.project import Project
from app.models.project_developer_relationship import ProjectDeveloperRelationship
from app.models.review_event import ReviewEvent
from app.models.social_capture import SocialCapture
from app.models.social_profile import SocialProfile
from app.models.source_evidence import SourceEvidence
from app.schemas.dashboard import BulkActionRequest, FieldVerificationCreate, OutreachActivityCreate, OutreachActivityUpdate, PaginatedResponse, PaginationMeta
from app.services.normalization import normalize_name

PROJECT_SORTS = {
    "name": Project.name,
    "created_at": Project.created_at,
    "updated_at": Project.updated_at,
    "lahore_zone": Project.lahore_zone,
    "project_type": Project.project_type,
    "project_status": Project.project_status,
    "review_status": Project.review_status,
    "outreach_status": Project.outreach_status,
    "last_outreach_at": Project.last_outreach_at,
    "next_follow_up_at": Project.next_follow_up_at,
}
DEVELOPER_SORTS = {
    "name": Developer.name,
    "created_at": Developer.created_at,
    "updated_at": Developer.updated_at,
    "review_status": Developer.review_status,
    "outreach_status": Developer.outreach_status,
    "last_outreach_at": Developer.last_outreach_at,
    "next_follow_up_at": Developer.next_follow_up_at,
}
REVIEW_STATUSES = {"unreviewed", "needs_review", "approved", "rejected", "excluded"}
OUTREACH_STATUSES = {"not_contacted", "research_needed", "ready_to_contact", "contacted", "follow_up_due", "interested", "meeting_scheduled", "onboarding", "onboarded", "not_interested", "invalid_contact", "do_not_contact"}
FIELD_ALLOWLIST = {"name", "developer_id", "project_type", "project_status", "address", "lahore_zone", "phone", "whatsapp", "email", "website", "latitude", "longitude", "classification"}
ACTIVITY_TYPES = {"research_note", "contact_attempt", "conversation", "meeting", "follow_up", "onboarding_update", "status_change", "do_not_contact"}
CHANNELS = {"phone", "whatsapp", "email", "facebook", "instagram", "linkedin", "x", "website_form", "in_person", "other", "none"}
DIRECTIONS = {"outbound", "inbound", "internal"}


def create_review_event(
    db: Session,
    *,
    action_type: str,
    developer_id: int | None = None,
    project_id: int | None = None,
    social_capture_id: int | None = None,
    classification_assessment_id: int | None = None,
    relationship_id: int | None = None,
    duplicate_candidate_id: int | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    note: str | None = None,
    operator_label: str = "Local Operator",
) -> ReviewEvent:
    event = ReviewEvent(
        developer_id=developer_id,
        project_id=project_id,
        social_capture_id=social_capture_id,
        classification_assessment_id=classification_assessment_id,
        relationship_id=relationship_id,
        duplicate_candidate_id=duplicate_candidate_id,
        action_type=action_type,
        before_json=json.dumps(before, default=str, sort_keys=True) if before is not None else None,
        after_json=json.dumps(after, default=str, sort_keys=True) if after is not None else None,
        note=note,
        operator_label=operator_label,
    )
    db.add(event)
    db.flush()
    return event


def _pagination(items: list[Any], total: int, offset: int, limit: int, filters: dict[str, Any]) -> PaginatedResponse:
    return PaginatedResponse(
        items=jsonable_encoder(items),
        pagination=PaginationMeta(offset=offset, limit=limit, returned=len(items), total=total, has_next=offset + len(items) < total, has_previous=offset > 0),
        applied_filters={key: value for key, value in filters.items() if value not in (None, "", False)},
    )


def _apply_project_filters(stmt, filters: dict[str, Any]):
    if not filters.get("include_merged"):
        stmt = stmt.where(Project.record_status == filters.get("record_status", "active"))
    elif filters.get("record_status"):
        stmt = stmt.where(Project.record_status == filters["record_status"])
    if filters.get("q"):
        q = f"%{normalize_name(filters['q']) or filters['q']}%"
        stmt = stmt.where(or_(Project.normalized_name.ilike(q), Project.address.ilike(q), Project.lahore_zone.ilike(q)))
    for column, key in ((Project.developer_id, "developer_id"), (Project.lahore_zone, "lahore_zone"), (Project.project_type, "project_type"), (Project.project_status, "project_status"), (Project.verification_status, "verification_status"), (Project.review_status, "review_status"), (Project.outreach_status, "outreach_status")):
        if filters.get(key) is not None:
            stmt = stmt.where(column == filters[key])
    if filters.get("developer_assignment") == "assigned":
        stmt = stmt.where(Project.developer_id.is_not(None))
    if filters.get("developer_assignment") == "missing":
        stmt = stmt.where(Project.developer_id.is_(None))
    if filters.get("has_coordinates") is True:
        stmt = stmt.where(Project.latitude.is_not(None), Project.longitude.is_not(None))
    if filters.get("has_coordinates") is False:
        stmt = stmt.where(or_(Project.latitude.is_(None), Project.longitude.is_(None)))
    if filters.get("has_website") is True:
        stmt = stmt.where(Project.official_website_url.is_not(None))
    if filters.get("has_website") is False:
        stmt = stmt.where(Project.official_website_url.is_(None))
    if filters.get("has_phone") is not None:
        stmt = stmt.where(exists().where(Contact.project_id == Project.id, Contact.contact_type.in_(["phone", "mobile", "landline"])) if filters["has_phone"] else ~exists().where(Contact.project_id == Project.id, Contact.contact_type.in_(["phone", "mobile", "landline"])))
    if filters.get("has_whatsapp") is not None:
        stmt = stmt.where(exists().where(Contact.project_id == Project.id, Contact.contact_type == "whatsapp") if filters["has_whatsapp"] else ~exists().where(Contact.project_id == Project.id, Contact.contact_type == "whatsapp"))
    if filters.get("has_email") is not None:
        stmt = stmt.where(exists().where(Contact.project_id == Project.id, Contact.contact_type == "email") if filters["has_email"] else ~exists().where(Contact.project_id == Project.id, Contact.contact_type == "email"))
    if filters.get("has_social_profile") is not None:
        stmt = stmt.where(exists().where(SocialProfile.project_id == Project.id) if filters["has_social_profile"] else ~exists().where(SocialProfile.project_id == Project.id))
    if filters.get("has_campaign_evidence") is not None:
        stmt = stmt.where(exists().where(CampaignEvidence.project_id == Project.id) if filters["has_campaign_evidence"] else ~exists().where(CampaignEvidence.project_id == Project.id))
    if filters.get("has_pending_relationship") is True:
        stmt = stmt.where(exists().where(ProjectDeveloperRelationship.project_id == Project.id, ProjectDeveloperRelationship.status == "candidate"))
    if filters.get("has_pending_duplicate") is True:
        stmt = stmt.where(exists().where(DuplicateCandidate.entity_type == "project", DuplicateCandidate.status == "pending", or_(DuplicateCandidate.left_project_id == Project.id, DuplicateCandidate.right_project_id == Project.id)))
    for key, column, op in (("created_after", Project.created_at, ">="), ("created_before", Project.created_at, "<="), ("updated_after", Project.updated_at, ">="), ("updated_before", Project.updated_at, "<=")):
        if filters.get(key):
            stmt = stmt.where(column >= filters[key] if op == ">=" else column <= filters[key])
    if all(filters.get(key) is not None for key in ("map_north", "map_south", "map_east", "map_west")):
        stmt = stmt.where(Project.latitude <= filters["map_north"], Project.latitude >= filters["map_south"], Project.longitude <= filters["map_east"], Project.longitude >= filters["map_west"])
    return stmt


def apply_project_filters_for_export(stmt, filters: dict[str, Any]):
    return _apply_project_filters(stmt, filters)


def list_projects_dashboard(db: Session, *, offset: int, limit: int, sort: str, direction: str, filters: dict[str, Any]) -> PaginatedResponse:
    if sort not in PROJECT_SORTS:
        raise InvalidOwnerError("Invalid project sort field.")
    if direction not in {"asc", "desc"}:
        raise InvalidOwnerError("Invalid sort direction.")
    stmt = _apply_project_filters(select(Project), filters)
    total = db.scalar(select(func.count()).select_from(_apply_project_filters(select(Project).subquery(), filters))) if False else len(db.scalars(stmt).all())
    column = PROJECT_SORTS[sort]
    stmt = stmt.order_by(column.asc() if direction == "asc" else column.desc(), Project.id.asc()).offset(offset).limit(min(limit, 100))
    items = list(db.scalars(stmt).all())
    return _pagination(items, total, offset, min(limit, 100), filters)


def _apply_developer_filters(stmt, filters: dict[str, Any]):
    if not filters.get("include_merged"):
        stmt = stmt.where(Developer.record_status == filters.get("record_status", "active"))
    elif filters.get("record_status"):
        stmt = stmt.where(Developer.record_status == filters["record_status"])
    if filters.get("q"):
        q = f"%{normalize_name(filters['q']) or filters['q']}%"
        stmt = stmt.where(or_(Developer.normalized_name.ilike(q), Developer.legal_name.ilike(q), Developer.office_address.ilike(q)))
    for column, key in ((Developer.classification, "classification"), (Developer.verification_status, "verification_status"), (Developer.review_status, "review_status"), (Developer.outreach_status, "outreach_status")):
        if filters.get(key) is not None:
            stmt = stmt.where(column == filters[key])
    if filters.get("has_website") is not None:
        stmt = stmt.where(Developer.website_url.is_not(None) if filters["has_website"] else Developer.website_url.is_(None))
    if filters.get("has_projects") is True:
        stmt = stmt.where(exists().where(Project.developer_id == Developer.id))
    if filters.get("has_lahore_projects") is True:
        stmt = stmt.where(exists().where(Project.developer_id == Developer.id, Project.city == "Lahore"))
    if filters.get("has_pending_duplicate") is True:
        stmt = stmt.where(exists().where(DuplicateCandidate.entity_type == "developer", DuplicateCandidate.status == "pending", or_(DuplicateCandidate.left_developer_id == Developer.id, DuplicateCandidate.right_developer_id == Developer.id)))
    return stmt


def apply_developer_filters_for_export(stmt, filters: dict[str, Any]):
    return _apply_developer_filters(stmt, filters)


def list_developers_dashboard(db: Session, *, offset: int, limit: int, sort: str, direction: str, filters: dict[str, Any]) -> PaginatedResponse:
    if sort not in DEVELOPER_SORTS:
        raise InvalidOwnerError("Invalid developer sort field.")
    if direction not in {"asc", "desc"}:
        raise InvalidOwnerError("Invalid sort direction.")
    stmt = _apply_developer_filters(select(Developer), filters)
    total = len(db.scalars(stmt).all())
    column = DEVELOPER_SORTS[sort]
    items = list(db.scalars(stmt.order_by(column.asc() if direction == "asc" else column.desc(), Developer.id.asc()).offset(offset).limit(min(limit, 100))).all())
    return _pagination(items, total, offset, min(limit, 100), filters)


def validate_map_bounds(north: float, south: float, east: float, west: float) -> None:
    if not (-90 <= south < north <= 90 and -180 <= west < east <= 180):
        raise InvalidOwnerError("Invalid map bounds.")
    if north - south > 1.2 or east - west > 1.2:
        raise InvalidOwnerError("Map bounds exceed the supported Lahore dashboard area.")


def map_projects(db: Session, *, north: float, south: float, east: float, west: float, limit: int, filters: dict[str, Any]) -> dict[str, Any]:
    validate_map_bounds(north, south, east, west)
    max_points = min(limit, get_settings().dashboard_map_max_points)
    filters = {**filters, "map_north": north, "map_south": south, "map_east": east, "map_west": west, "has_coordinates": True}
    stmt = _apply_project_filters(select(Project), filters)
    total = len(db.scalars(stmt).all())
    projects = list(db.scalars(stmt.limit(max_points)).all())
    items = []
    for project in projects:
        items.append({
            "id": project.id,
            "name": project.name,
            "latitude": project.latitude,
            "longitude": project.longitude,
            "project_type": project.project_type,
            "classification": getattr(project, "classification", None),
            "review_status": project.review_status,
            "outreach_status": project.outreach_status,
            "developer": {"id": project.developer.id, "name": project.developer.name} if project.developer else None,
            "pending_duplicate": db.scalar(select(DuplicateCandidate.id).where(DuplicateCandidate.entity_type == "project", DuplicateCandidate.status == "pending", or_(DuplicateCandidate.left_project_id == project.id, DuplicateCandidate.right_project_id == project.id)).limit(1)) is not None,
            "pending_relationship": db.scalar(select(ProjectDeveloperRelationship.id).where(ProjectDeveloperRelationship.project_id == project.id, ProjectDeveloperRelationship.status == "candidate").limit(1)) is not None,
        })
    return {"items": items, "total_matching": total, "returned": len(items), "truncated": total > len(items)}


def dashboard_summary(db: Session, filters: dict[str, Any]) -> dict[str, Any]:
    base = _apply_project_filters(select(Project), {**filters, "record_status": "active"})
    projects = list(db.scalars(base).all())
    project_ids = [project.id for project in projects]
    now = utc_now()
    return {
        "projects": {
            "total_active": len(projects),
            "approved": sum(1 for p in projects if p.review_status == "approved"),
            "needs_review": sum(1 for p in projects if p.review_status == "needs_review"),
            "unreviewed": sum(1 for p in projects if p.review_status == "unreviewed"),
            "unassigned_developer": sum(1 for p in projects if p.developer_id is None),
        },
        "intelligence": {
            "pending_duplicates": db.scalar(select(func.count()).select_from(DuplicateCandidate).where(DuplicateCandidate.status == "pending")) or 0,
            "pending_relationships": db.scalar(select(func.count()).select_from(ProjectDeveloperRelationship).where(ProjectDeveloperRelationship.status == "candidate")) or 0,
            "pending_classifications": db.scalar(select(func.count()).select_from(ClassificationAssessment).where(ClassificationAssessment.assessment_status == "pending")) or 0,
        },
        "data_completeness": {
            "with_phone": _count_projects_with(db, project_ids, Contact, Contact.contact_type.in_(["phone", "mobile", "landline"])),
            "with_whatsapp": _count_projects_with(db, project_ids, Contact, Contact.contact_type == "whatsapp"),
            "with_website": sum(1 for p in projects if p.official_website_url),
            "with_social_profile": _count_projects_with(db, project_ids, SocialProfile, True),
            "with_campaign_evidence": _count_projects_with(db, project_ids, CampaignEvidence, True),
            "with_coordinates": sum(1 for p in projects if p.latitude is not None and p.longitude is not None),
        },
        "outreach": {status: sum(1 for p in projects if p.outreach_status == status) for status in ["not_contacted", "ready_to_contact", "contacted", "follow_up_due", "interested", "onboarding", "onboarded"]},
        "jobs": {
            "worker_online": False,
            "queued": db.scalar(select(func.count()).select_from(CollectionJob).where(CollectionJob.status == "queued")) or 0,
            "running": db.scalar(select(func.count()).select_from(CollectionJob).where(CollectionJob.status == "running")) or 0,
            "failed": db.scalar(select(func.count()).select_from(CollectionJob).where(CollectionJob.status == "failed")) or 0,
        },
        "social": {"pending": db.scalar(select(func.count()).select_from(SocialCapture).where(SocialCapture.review_status.in_(["unassigned", "review_required"]))) or 0},
        "follow_up_due": sum(1 for p in projects if p.next_follow_up_at and p.next_follow_up_at <= now and p.outreach_status not in {"onboarded", "not_interested", "invalid_contact", "do_not_contact"}),
    }


def _count_projects_with(db: Session, project_ids: list[int], model: Any, condition: Any) -> int:
    if not project_ids:
        return 0
    stmt = select(func.count(func.distinct(model.project_id))).where(model.project_id.in_(project_ids))
    if condition is not True:
        stmt = stmt.where(condition)
    return db.scalar(stmt) or 0


def project_detail(db: Session, project_id: int) -> dict[str, Any]:
    project = db.get(Project, project_id)
    if project is None:
        raise EntityNotFoundError(f"Project {project_id} was not found.")
    return {
        "project": project,
        "developer": project.developer,
        "contacts": list(db.scalars(select(Contact).where(Contact.project_id == project_id).limit(50)).all()),
        "social_profiles": list(db.scalars(select(SocialProfile).where(SocialProfile.project_id == project_id).limit(50)).all()),
        "campaign_evidence_count": db.scalar(select(func.count()).select_from(CampaignEvidence).where(CampaignEvidence.project_id == project_id)) or 0,
        "source_evidence_count": db.scalar(select(func.count()).select_from(SourceEvidence).where(SourceEvidence.project_id == project_id)) or 0,
        "classification": db.scalar(select(ClassificationAssessment).where(ClassificationAssessment.project_id == project_id).order_by(ClassificationAssessment.created_at.desc()).limit(1)),
        "relationships": list(db.scalars(select(ProjectDeveloperRelationship).where(ProjectDeveloperRelationship.project_id == project_id).limit(20)).all()),
        "duplicate_candidates": list(db.scalars(select(DuplicateCandidate).where(DuplicateCandidate.entity_type == "project", or_(DuplicateCandidate.left_project_id == project_id, DuplicateCandidate.right_project_id == project_id)).limit(20)).all()),
        "outreach": list(db.scalars(select(OutreachActivity).where(OutreachActivity.project_id == project_id).order_by(OutreachActivity.occurred_at.desc()).limit(20)).all()),
        "history": list(db.scalars(select(ReviewEvent).where(ReviewEvent.project_id == project_id).order_by(ReviewEvent.created_at.desc()).limit(20)).all()),
        "merged_into_project_id": project.merged_into_project_id,
    }


def developer_detail(db: Session, developer_id: int) -> dict[str, Any]:
    developer = db.get(Developer, developer_id)
    if developer is None:
        raise EntityNotFoundError(f"Developer {developer_id} was not found.")
    return {
        "developer": developer,
        "projects": list(db.scalars(select(Project).where(Project.developer_id == developer_id).limit(50)).all()),
        "contacts": list(db.scalars(select(Contact).where(Contact.developer_id == developer_id).limit(50)).all()),
        "social_profiles": list(db.scalars(select(SocialProfile).where(SocialProfile.developer_id == developer_id).limit(50)).all()),
        "classification": db.scalar(select(ClassificationAssessment).where(ClassificationAssessment.developer_id == developer_id).order_by(ClassificationAssessment.created_at.desc()).limit(1)),
        "duplicate_candidates": list(db.scalars(select(DuplicateCandidate).where(DuplicateCandidate.entity_type == "developer", or_(DuplicateCandidate.left_developer_id == developer_id, DuplicateCandidate.right_developer_id == developer_id)).limit(20)).all()),
        "outreach": list(db.scalars(select(OutreachActivity).where(OutreachActivity.developer_id == developer_id).order_by(OutreachActivity.occurred_at.desc()).limit(20)).all()),
        "history": list(db.scalars(select(ReviewEvent).where(ReviewEvent.developer_id == developer_id).order_by(ReviewEvent.created_at.desc()).limit(20)).all()),
        "merged_into_developer_id": developer.merged_into_developer_id,
    }


def create_field_verification(db: Session, payload: FieldVerificationCreate) -> FieldVerification:
    if payload.field_name not in FIELD_ALLOWLIST:
        raise InvalidOwnerError("Unsupported field for verification.")
    owner = db.get(Developer, payload.developer_id) if payload.developer_id else db.get(Project, payload.project_id)
    if owner is None:
        raise EntityNotFoundError("Verification owner was not found.")
    verification = FieldVerification(**payload.model_dump(), verified_at=utc_now())
    db.add(verification)
    create_review_event(db, action_type="field_verified", developer_id=payload.developer_id, project_id=payload.project_id, after=payload.model_dump(), note=payload.review_note)
    db.commit()
    db.refresh(verification)
    return verification


def create_outreach_activity(db: Session, payload: OutreachActivityCreate) -> OutreachActivity:
    if payload.activity_type not in ACTIVITY_TYPES or payload.channel not in CHANNELS or payload.direction not in DIRECTIONS:
        raise InvalidOwnerError("Invalid outreach activity type, channel, or direction.")
    owner = db.get(Developer, payload.developer_id) if payload.developer_id else db.get(Project, payload.project_id)
    if owner is None:
        raise EntityNotFoundError("Outreach owner was not found.")
    if owner.record_status != "active":
        raise ConflictError("Merged records cannot receive outreach activity.")
    activity = OutreachActivity(**{**payload.model_dump(), "occurred_at": payload.occurred_at or utc_now()})
    db.add(activity)
    before = {"outreach_status": owner.outreach_status, "next_follow_up_at": owner.next_follow_up_at}
    if payload.status_after:
        if payload.status_after not in OUTREACH_STATUSES:
            raise InvalidOwnerError("Invalid outreach status.")
        owner.outreach_status = payload.status_after
        owner.last_outreach_at = activity.occurred_at
    if payload.follow_up_at:
        owner.next_follow_up_at = payload.follow_up_at
    owner.version_number += 1
    create_review_event(db, action_type="outreach_activity_added", developer_id=payload.developer_id, project_id=payload.project_id, before=before, after=payload.model_dump(), note=payload.note)
    db.commit()
    db.refresh(activity)
    return activity


def list_outreach_activities(db: Session, *, offset: int, limit: int, filters: dict[str, Any]) -> list[OutreachActivity]:
    stmt = select(OutreachActivity)
    for column, key in ((OutreachActivity.developer_id, "developer_id"), (OutreachActivity.project_id, "project_id"), (OutreachActivity.activity_type, "activity_type"), (OutreachActivity.channel, "channel")):
        if filters.get(key) is not None:
            stmt = stmt.where(column == filters[key])
    return list(db.scalars(stmt.order_by(OutreachActivity.occurred_at.desc()).offset(offset).limit(min(limit, 100))).all())


def update_outreach_activity(db: Session, activity_id: int, payload: OutreachActivityUpdate) -> OutreachActivity:
    activity = db.get(OutreachActivity, activity_id)
    if activity is None:
        raise EntityNotFoundError(f"Outreach activity {activity_id} was not found.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(activity, key, value)
    db.commit()
    db.refresh(activity)
    return activity


def bulk_action(db: Session, payload: BulkActionRequest) -> dict[str, Any]:
    ids = list(dict.fromkeys(payload.entity_ids))[:100]
    model = Project if payload.entity_type == "project" else Developer
    results = []
    updated = 0
    for item_id in ids:
        item = db.get(model, item_id)
        if item is None:
            results.append({"id": item_id, "status": "failed", "reason": "Not found"})
            continue
        if item.record_status != "active":
            results.append({"id": item_id, "status": "failed", "reason": "Record is merged."})
            continue
        before = {"review_status": item.review_status, "outreach_status": item.outreach_status, "review_note": item.review_note}
        if payload.action in {"set_review_status", "exclude"}:
            item.review_status = "excluded" if payload.action == "exclude" else payload.payload.get("review_status", item.review_status)
            item.review_note = payload.payload.get("note")
            item.last_reviewed_at = utc_now()
        elif payload.action == "set_outreach_status":
            status = payload.payload.get("outreach_status")
            if status not in OUTREACH_STATUSES:
                results.append({"id": item_id, "status": "failed", "reason": "Invalid outreach status"})
                continue
            item.outreach_status = status
        elif payload.action == "add_review_note":
            item.review_note = payload.payload.get("note")
        item.version_number += 1
        create_review_event(db, action_type="record_excluded" if payload.action == "exclude" else payload.action, developer_id=item_id if payload.entity_type == "developer" else None, project_id=item_id if payload.entity_type == "project" else None, before=before, after={"review_status": item.review_status, "outreach_status": item.outreach_status, "review_note": item.review_note}, note=payload.payload.get("note"))
        updated += 1
        results.append({"id": item_id, "status": "updated"})
    db.commit()
    return {"requested": len(ids), "updated": updated, "failed": len(ids) - updated, "results": results}

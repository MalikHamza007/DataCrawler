from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError
from app.db.base import utc_now
from app.models.contact import Contact
from app.models.developer import Developer
from app.models.intelligence import ClassificationAssessment, DuplicateCandidate, MergeOperation
from app.models.project import Project
from app.models.project_developer_relationship import ProjectDeveloperRelationship
from app.models.project_discovery import ProjectDiscovery
from app.models.social_profile import SocialProfile
from app.models.source_evidence import SourceEvidence
from app.models.website_crawl import WebsiteCrawl


def merge_preview(db: Session, candidate_id: int, survivor_id: int) -> dict:
    candidate = _candidate(db, candidate_id); pair = _pair(candidate)
    if survivor_id not in pair: raise ValueError("Survivor must belong to the duplicate candidate pair")
    absorbed_id = pair[1] if survivor_id == pair[0] else pair[0]
    model = Developer if candidate.entity_type == "developer" else Project
    survivor, absorbed = db.get(model, survivor_id), db.get(model, absorbed_id)
    if not survivor or not absorbed or survivor.record_status != "active" or absorbed.record_status != "active": raise ConflictError("Both records must remain active")
    fields = _fields(candidate.entity_type); actions = {}; conflicts = {}
    for field in fields:
        left, right = getattr(survivor, field), getattr(absorbed, field)
        action = "fill_survivor" if not left and right else "keep_survivor"
        actions[field] = {"survivor": left, "absorbed": right, "action": action}
        if left and right and left != right: conflicts[field] = {"survivor": left, "absorbed": right, "selected": left, "reason": "Survivor value preserved"}
    owner = Contact.developer_id if candidate.entity_type == "developer" else Contact.project_id
    social_owner = SocialProfile.developer_id if candidate.entity_type == "developer" else SocialProfile.project_id
    preview = {"entity_type": candidate.entity_type, "candidate_id": candidate.id, "survivor_id": survivor_id, "absorbed_id": absorbed_id, "field_actions": actions, "field_conflicts": conflicts,
        "contacts": _child_counts(db, Contact, owner, survivor_id, absorbed_id, (Contact.contact_type, Contact.normalized_value)),
        "social_profiles": _child_counts(db, SocialProfile, social_owner, survivor_id, absorbed_id, (SocialProfile.platform, SocialProfile.normalized_url)),
        "evidence_to_move": db.scalar(select(func.count()).select_from(SourceEvidence).where((SourceEvidence.developer_id if candidate.entity_type == "developer" else SourceEvidence.project_id) == absorbed_id)) or 0,
        "projects_to_reassign": db.scalar(select(func.count()).select_from(Project).where(Project.developer_id == absorbed_id)) if candidate.entity_type == "developer" else 0,
        "relationships_affected": db.scalar(select(func.count()).select_from(ProjectDeveloperRelationship).where((ProjectDeveloperRelationship.developer_id if candidate.entity_type == "developer" else ProjectDeveloperRelationship.project_id) == absorbed_id)) or 0,
        "discoveries_affected": db.scalar(select(func.count()).select_from(ProjectDiscovery).where(ProjectDiscovery.project_id == absorbed_id)) if candidate.entity_type == "project" else 0,
        "website_crawls_affected": db.scalar(select(func.count()).select_from(WebsiteCrawl).where((WebsiteCrawl.developer_id if candidate.entity_type == "developer" else WebsiteCrawl.project_id) == absorbed_id)) or 0,
        "campaign_evidence_affected": 0, "outreach_activity_affected": 0, "warnings": []}
    if candidate.entity_type == "project" and survivor.developer_id and absorbed.developer_id and survivor.developer_id != absorbed.developer_id:
        preview["warnings"].append("Projects have different assigned developers; resolve before merge")
    return preview


def execute_merge(db: Session, candidate_id: int, survivor_id: int, operator_note: str | None = None) -> MergeOperation:
    candidate = _candidate(db, candidate_id); preview = merge_preview(db, candidate_id, survivor_id); absorbed_id = preview["absorbed_id"]
    if candidate.status not in {"pending", "confirmed_duplicate"}: raise ConflictError("Candidate status does not allow merging")
    if candidate.entity_type == "project" and preview["warnings"]: raise ConflictError(preview["warnings"][0])
    operation = MergeOperation(entity_type=candidate.entity_type, survivor_developer_id=survivor_id if candidate.entity_type == "developer" else None, absorbed_developer_id=absorbed_id if candidate.entity_type == "developer" else None, survivor_project_id=survivor_id if candidate.entity_type == "project" else None, absorbed_project_id=absorbed_id if candidate.entity_type == "project" else None, duplicate_candidate_id=candidate.id, preview_json=preview, operator_note=operator_note, status="previewed")
    db.add(operation); db.flush()
    try:
        if candidate.entity_type == "developer": _merge_developer(db, survivor_id, absorbed_id, preview)
        else: _merge_project(db, survivor_id, absorbed_id, preview)
        candidate.status = "merged"; candidate.merge_operation_id = operation.id; operation.status = "completed"; operation.actions_json = preview["field_actions"]; operation.conflicts_json = preview["field_conflicts"]; operation.completed_at = utc_now()
        db.commit(); db.refresh(operation); return operation
    except Exception as exc:
        db.rollback()
        failed = MergeOperation(entity_type=candidate.entity_type, survivor_developer_id=survivor_id if candidate.entity_type == "developer" else None, absorbed_developer_id=absorbed_id if candidate.entity_type == "developer" else None, survivor_project_id=survivor_id if candidate.entity_type == "project" else None, absorbed_project_id=absorbed_id if candidate.entity_type == "project" else None, duplicate_candidate_id=candidate_id, preview_json=preview, conflicts_json={"failure": str(exc)}, operator_note=operator_note, status="failed")
        db.add(failed); db.commit()
        raise


def _merge_developer(db: Session, survivor_id: int, absorbed_id: int, preview: dict) -> None:
    survivor, absorbed = db.get(Developer, survivor_id), db.get(Developer, absorbed_id); _fill(survivor, absorbed, _fields("developer"))
    db.query(Project).filter(Project.developer_id == absorbed_id).update({Project.developer_id: survivor_id})
    _move_children(db, Contact, Contact.developer_id, survivor_id, absorbed_id, (Contact.contact_type, Contact.normalized_value))
    _move_children(db, SocialProfile, SocialProfile.developer_id, survivor_id, absorbed_id, (SocialProfile.platform, SocialProfile.normalized_url))
    _move_evidence(db, SourceEvidence.developer_id, survivor_id, absorbed_id)
    db.query(WebsiteCrawl).filter(WebsiteCrawl.developer_id == absorbed_id).update({WebsiteCrawl.developer_id: survivor_id})
    _move_assessments(db, "developer", survivor_id, absorbed_id)
    for relationship in list(db.scalars(select(ProjectDeveloperRelationship).where(ProjectDeveloperRelationship.developer_id == absorbed_id)).all()):
        existing = db.scalar(select(ProjectDeveloperRelationship).where(ProjectDeveloperRelationship.project_id == relationship.project_id, ProjectDeveloperRelationship.developer_id == survivor_id, ProjectDeveloperRelationship.relationship_type == relationship.relationship_type, ProjectDeveloperRelationship.source_url == relationship.source_url))
        if existing: db.delete(relationship)
        else: relationship.developer_id = survivor_id
    absorbed.record_status = "merged"; absorbed.merged_into_developer_id = survivor_id; absorbed.merged_at = utc_now()


def _merge_project(db: Session, survivor_id: int, absorbed_id: int, preview: dict) -> None:
    survivor, absorbed = db.get(Project, survivor_id), db.get(Project, absorbed_id); _fill(survivor, absorbed, tuple(field for field in _fields("project") if field != "google_place_id"))
    if not survivor.developer_id: survivor.developer_id = absorbed.developer_id
    _move_children(db, Contact, Contact.project_id, survivor_id, absorbed_id, (Contact.contact_type, Contact.normalized_value))
    _move_children(db, SocialProfile, SocialProfile.project_id, survivor_id, absorbed_id, (SocialProfile.platform, SocialProfile.normalized_url))
    _move_evidence(db, SourceEvidence.project_id, survivor_id, absorbed_id)
    db.query(ProjectDiscovery).filter(ProjectDiscovery.project_id == absorbed_id).update({ProjectDiscovery.project_id: survivor_id})
    db.query(WebsiteCrawl).filter(WebsiteCrawl.project_id == absorbed_id).update({WebsiteCrawl.project_id: survivor_id})
    _move_assessments(db, "project", survivor_id, absorbed_id)
    for relationship in list(db.scalars(select(ProjectDeveloperRelationship).where(ProjectDeveloperRelationship.project_id == absorbed_id)).all()):
        existing = db.scalar(select(ProjectDeveloperRelationship).where(ProjectDeveloperRelationship.project_id == survivor_id, ProjectDeveloperRelationship.developer_id == relationship.developer_id, ProjectDeveloperRelationship.relationship_type == relationship.relationship_type, ProjectDeveloperRelationship.source_url == relationship.source_url))
        if existing: db.delete(relationship)
        else: relationship.project_id = survivor_id
    absorbed.record_status = "merged"; absorbed.merged_into_project_id = survivor_id; absorbed.merged_at = utc_now()


def _move_children(db: Session, model: type, owner: object, survivor: int, absorbed: int, keys: tuple) -> None:
    existing = {tuple(getattr(item, key.key) for key in keys) for item in db.scalars(select(model).where(owner == survivor)).all()}
    for child in list(db.scalars(select(model).where(owner == absorbed)).all()):
        key = tuple(getattr(child, column.key) for column in keys)
        if key in existing: db.delete(child)
        else: setattr(child, owner.key, survivor); existing.add(key)


def _child_counts(db: Session, model: type, owner: object, survivor: int, absorbed: int, keys: tuple) -> dict:
    current = {tuple(getattr(item, key.key) for key in keys) for item in db.scalars(select(model).where(owner == survivor)).all()}; move = duplicates = 0
    for item in db.scalars(select(model).where(owner == absorbed)).all():
        if tuple(getattr(item, key.key) for key in keys) in current: duplicates += 1
        else: move += 1
    return {"move": move, "exact_duplicates": duplicates}


def _move_evidence(db: Session, owner: object, survivor: int, absorbed: int) -> None:
    existing = {(item.source_url, item.field_name, item.extracted_value) for item in db.scalars(select(SourceEvidence).where(owner == survivor)).all()}
    for item in list(db.scalars(select(SourceEvidence).where(owner == absorbed)).all()):
        key = (item.source_url, item.field_name, item.extracted_value)
        if key in existing: db.delete(item)
        else: setattr(item, owner.key, survivor); existing.add(key)


def _move_assessments(db: Session, entity_type: str, survivor: int, absorbed: int) -> None:
    owner = ClassificationAssessment.developer_id if entity_type == "developer" else ClassificationAssessment.project_id
    existing_versions = {item.rule_version for item in db.scalars(select(ClassificationAssessment).where(owner == survivor)).all()}
    for item in list(db.scalars(select(ClassificationAssessment).where(owner == absorbed)).all()):
        if item.rule_version in existing_versions: db.delete(item)
        else: setattr(item, owner.key, survivor); existing_versions.add(item.rule_version)


def _candidate(db: Session, candidate_id: int) -> DuplicateCandidate:
    candidate = db.get(DuplicateCandidate, candidate_id)
    if not candidate: raise ValueError("Duplicate candidate was not found")
    return candidate


def _pair(candidate: DuplicateCandidate) -> tuple[int, int]:
    return (candidate.left_developer_id, candidate.right_developer_id) if candidate.entity_type == "developer" else (candidate.left_project_id, candidate.right_project_id)


def _fields(entity_type: str) -> tuple[str, ...]:
    return ("name", "legal_name", "description", "website_url", "office_address", "city", "country") if entity_type == "developer" else ("name", "description", "project_type", "project_status", "address", "lahore_zone", "city", "country", "latitude", "longitude", "google_place_id", "google_maps_url", "official_website_url")


def _fill(survivor: object, absorbed: object, fields: tuple[str, ...]) -> None:
    for field in fields:
        if getattr(survivor, field) in {None, ""} and getattr(absorbed, field) not in {None, ""}: setattr(survivor, field, getattr(absorbed, field))

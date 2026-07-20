from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select

from app.api.dependencies import DbSession, pagination
from app.core.config import get_settings
from app.db.base import utc_now
from app.intelligence.classification import assess_developer, assess_project, review_assessment
from app.intelligence.duplicates import scan_duplicates
from app.intelligence.merging import execute_merge, merge_preview
from app.intelligence.relationships import reject_relationship, score_relationship, verify_relationship
from app.models.collection_job import CollectionJob
from app.models.intelligence import ClassificationAssessment, DuplicateCandidate
from app.models.project_developer_relationship import ProjectDeveloperRelationship
from app.schemas.collection_job import CollectionJobRead
from app.schemas.intelligence import AssessmentRead, DuplicateRead, DuplicateScanRequest, MergeOperationRead, MergePreviewRequest, MergeRequest, OverrideRequest, RelationshipRead, ReviewNote

router = APIRouter(tags=["Intelligence Review"])


def _bad(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=404 if "not found" in str(exc).casefold() else 400, detail=str(exc))


@router.post("/developers/{developer_id}/classification/recalculate", response_model=AssessmentRead)
def recalculate_developer(developer_id: int, db: DbSession) -> object:
    try: return assess_developer(db, developer_id)
    except ValueError as exc: raise _bad(exc) from exc


@router.post("/projects/{project_id}/classification/recalculate", response_model=AssessmentRead)
def recalculate_project(project_id: int, db: DbSession) -> object:
    try: return assess_project(db, project_id)
    except ValueError as exc: raise _bad(exc) from exc


@router.get("/classification-assessments", response_model=list[AssessmentRead])
def list_assessments(db: DbSession, page: Annotated[tuple[int, int], Depends(pagination)], entity_type: str | None = None, suggested_classification: str | None = None, assessment_status: str | None = None, confidence_level: str | None = None, minimum_score: int | None = None, maximum_score: int | None = None, rule_version: str | None = None) -> list[object]:
    offset, limit = page; stmt = select(ClassificationAssessment)
    for column, value in ((ClassificationAssessment.entity_type, entity_type), (ClassificationAssessment.suggested_classification, suggested_classification), (ClassificationAssessment.assessment_status, assessment_status), (ClassificationAssessment.confidence_level, confidence_level), (ClassificationAssessment.rule_version, rule_version)):
        if value is not None: stmt = stmt.where(column == value)
    if minimum_score is not None: stmt = stmt.where(ClassificationAssessment.system_score >= minimum_score)
    if maximum_score is not None: stmt = stmt.where(ClassificationAssessment.system_score <= maximum_score)
    return list(db.scalars(stmt.order_by(ClassificationAssessment.created_at.desc()).offset(offset).limit(min(limit, 100))).all())


@router.get("/classification-assessments/{assessment_id}", response_model=AssessmentRead)
def get_assessment(assessment_id: int, db: DbSession) -> object:
    value = db.get(ClassificationAssessment, assessment_id)
    if not value: raise HTTPException(404, "Assessment not found")
    return value


@router.post("/classification-assessments/{assessment_id}/confirm", response_model=AssessmentRead)
def confirm_assessment(assessment_id: int, payload: ReviewNote, db: DbSession) -> object:
    try: return review_assessment(db, assessment_id, "confirm", None, payload.review_note)
    except ValueError as exc: raise _bad(exc) from exc


@router.post("/classification-assessments/{assessment_id}/override", response_model=AssessmentRead)
def override_assessment(assessment_id: int, payload: OverrideRequest, db: DbSession) -> object:
    try: return review_assessment(db, assessment_id, "override", payload.manual_classification, payload.review_note)
    except ValueError as exc: raise _bad(exc) from exc


@router.post("/classification-assessments/{assessment_id}/reject", response_model=AssessmentRead)
def reject_assessment(assessment_id: int, payload: ReviewNote, db: DbSession) -> object:
    try: return review_assessment(db, assessment_id, "reject", None, payload.review_note)
    except ValueError as exc: raise _bad(exc) from exc


@router.get("/project-developer-relationships", response_model=list[RelationshipRead])
def list_relationships(db: DbSession, page: Annotated[tuple[int, int], Depends(pagination)], project_id: int | None = None, developer_id: int | None = None, status_value: str | None = Query(default=None, alias="status"), confidence_level: str | None = None, minimum_score: int | None = None, maximum_score: int | None = None, rule_version: str | None = None) -> list[object]:
    offset, limit = page; stmt = select(ProjectDeveloperRelationship)
    for column, value in ((ProjectDeveloperRelationship.project_id, project_id), (ProjectDeveloperRelationship.developer_id, developer_id), (ProjectDeveloperRelationship.status, status_value), (ProjectDeveloperRelationship.confidence_level, confidence_level), (ProjectDeveloperRelationship.rule_version, rule_version)):
        if value is not None: stmt = stmt.where(column == value)
    if minimum_score is not None: stmt = stmt.where(ProjectDeveloperRelationship.system_score >= minimum_score)
    if maximum_score is not None: stmt = stmt.where(ProjectDeveloperRelationship.system_score <= maximum_score)
    return list(db.scalars(stmt.offset(offset).limit(min(limit, 100))).all())


@router.get("/project-developer-relationships/{relationship_id}", response_model=RelationshipRead)
def get_relationship(relationship_id: int, db: DbSession) -> object:
    value = db.get(ProjectDeveloperRelationship, relationship_id)
    if not value: raise HTTPException(404, "Relationship not found")
    return value


@router.post("/project-developer-relationships/{relationship_id}/recalculate", response_model=RelationshipRead)
def recalculate_relationship(relationship_id: int, db: DbSession) -> object:
    try: return score_relationship(db, relationship_id)
    except ValueError as exc: raise _bad(exc) from exc


@router.post("/project-developer-relationships/{relationship_id}/verify", response_model=RelationshipRead)
def verify(relationship_id: int, payload: ReviewNote, db: DbSession) -> object:
    try: return verify_relationship(db, relationship_id, payload.review_note)
    except ValueError as exc: raise _bad(exc) from exc


@router.post("/project-developer-relationships/{relationship_id}/reject", response_model=RelationshipRead)
def reject(relationship_id: int, payload: ReviewNote, db: DbSession) -> object:
    try: return reject_relationship(db, relationship_id, payload.review_note)
    except ValueError as exc: raise _bad(exc) from exc


@router.post("/duplicate-scans", response_model=CollectionJobRead, status_code=status.HTTP_201_CREATED)
def create_duplicate_scan(payload: DuplicateScanRequest, db: DbSession) -> object:
    settings = get_settings(); config = payload.model_dump(); config["rule_version"] = settings.intelligence_rule_version
    job = CollectionJob(job_type="duplicate_scan", status="queued", city="Lahore", lahore_zone=payload.lahore_zone, search_config_json=config, progress_phase="queued", max_attempts=settings.worker_max_job_attempts)
    db.add(job); db.commit(); db.refresh(job); return job


@router.get("/duplicate-candidates", response_model=list[DuplicateRead])
def list_duplicates(db: DbSession, page: Annotated[tuple[int, int], Depends(pagination)], entity_type: str | None = None, status_value: str | None = Query(default=None, alias="status"), minimum_score: int | None = None) -> list[object]:
    offset, limit = page; stmt = select(DuplicateCandidate)
    if entity_type: stmt = stmt.where(DuplicateCandidate.entity_type == entity_type)
    if status_value: stmt = stmt.where(DuplicateCandidate.status == status_value)
    if minimum_score is not None: stmt = stmt.where(DuplicateCandidate.duplicate_score >= minimum_score)
    return list(db.scalars(stmt.order_by(DuplicateCandidate.duplicate_score.desc()).offset(offset).limit(min(limit, 100))).all())


@router.get("/duplicate-candidates/{candidate_id}", response_model=DuplicateRead)
def get_duplicate(candidate_id: int, db: DbSession) -> object:
    value = db.get(DuplicateCandidate, candidate_id)
    if not value: raise HTTPException(404, "Duplicate candidate not found")
    return value


def _review_duplicate(db: DbSession, candidate_id: int, status_value: str, note: str) -> DuplicateCandidate:
    value = db.get(DuplicateCandidate, candidate_id)
    if not value: raise HTTPException(404, "Duplicate candidate not found")
    value.status = status_value; value.review_note = note; value.reviewed_at = utc_now(); db.commit(); db.refresh(value); return value


@router.post("/duplicate-candidates/{candidate_id}/confirm", response_model=DuplicateRead)
def confirm_duplicate(candidate_id: int, payload: ReviewNote, db: DbSession) -> object: return _review_duplicate(db, candidate_id, "confirmed_duplicate", payload.review_note)


@router.post("/duplicate-candidates/{candidate_id}/not-duplicate", response_model=DuplicateRead)
def not_duplicate(candidate_id: int, payload: ReviewNote, db: DbSession) -> object: return _review_duplicate(db, candidate_id, "not_duplicate", payload.review_note)


@router.post("/duplicate-candidates/{candidate_id}/dismiss", response_model=DuplicateRead)
def dismiss(candidate_id: int, payload: ReviewNote, db: DbSession) -> object: return _review_duplicate(db, candidate_id, "dismissed", payload.review_note)


@router.post("/duplicate-candidates/{candidate_id}/merge-preview")
def preview_merge(candidate_id: int, payload: MergePreviewRequest, db: DbSession) -> dict:
    try: return merge_preview(db, candidate_id, payload.survivor_id)
    except ValueError as exc: raise _bad(exc) from exc


@router.post("/duplicate-candidates/{candidate_id}/merge", response_model=MergeOperationRead)
def merge(candidate_id: int, payload: MergeRequest, db: DbSession) -> object:
    try: return execute_merge(db, candidate_id, payload.survivor_id, payload.operator_note)
    except ValueError as exc: raise _bad(exc) from exc

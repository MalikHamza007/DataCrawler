from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class AssessmentRead(ORMModel):
    id: int; developer_id: int | None; project_id: int | None; entity_type: str; suggested_classification: str; system_score: int; confidence_level: str; signals_json: list; explanation: str; rule_version: str; assessment_status: str; manual_classification: str | None; manual_note: str | None; manually_reviewed: bool; reviewed_at: datetime | None; effective_classification: str; created_at: datetime; updated_at: datetime


class ReviewNote(BaseModel):
    review_note: str = Field(min_length=1, max_length=2000)


class OverrideRequest(ReviewNote):
    manual_classification: str = Field(min_length=1, max_length=50)


class RelationshipRead(ORMModel):
    id: int; project_id: int; developer_id: int; relationship_type: str; status: str; source_evidence_id: int | None; source_url: str; evidence_text: str; system_score: int | None; confidence_level: str | None; signals_json: list | None; explanation: str | None; rule_version: str | None; evaluated_at: datetime | None; reviewed_at: datetime | None; review_note: str | None; created_at: datetime; updated_at: datetime


class DuplicateScanRequest(BaseModel):
    entity_type: Literal["developer", "project"]
    lahore_zone: str | None = Field(default=None, max_length=150)
    include_merged_records: bool = False
    minimum_score: int | None = Field(default=None, ge=0, le=100)


class DuplicateRead(ORMModel):
    id: int; entity_type: str; left_developer_id: int | None; right_developer_id: int | None; left_project_id: int | None; right_project_id: int | None; duplicate_score: int; confidence_level: str; signals_json: list; explanation: str; rule_version: str; status: str; review_note: str | None; reviewed_at: datetime | None; merge_operation_id: int | None; created_at: datetime; updated_at: datetime


class MergePreviewRequest(BaseModel):
    survivor_id: int


class MergeRequest(MergePreviewRequest):
    operator_note: str | None = Field(default=None, max_length=2000)


class MergeOperationRead(ORMModel):
    id: int; entity_type: str; survivor_developer_id: int | None; absorbed_developer_id: int | None; survivor_project_id: int | None; absorbed_project_id: int | None; duplicate_candidate_id: int | None; preview_json: dict; actions_json: dict | None; conflicts_json: dict | None; operator_note: str | None; status: str; created_at: datetime; completed_at: datetime | None

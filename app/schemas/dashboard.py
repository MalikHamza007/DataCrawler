from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field, model_validator

from app.schemas.common import ORMModel


class PaginationMeta(ORMModel):
    offset: int
    limit: int
    returned: int
    total: int
    has_next: bool
    has_previous: bool


class PaginatedResponse(ORMModel):
    items: list[Any]
    pagination: PaginationMeta
    applied_filters: dict[str, Any]


class ReviewEventRead(ORMModel):
    id: int
    developer_id: int | None
    project_id: int | None
    social_capture_id: int | None
    classification_assessment_id: int | None
    relationship_id: int | None
    duplicate_candidate_id: int | None
    action_type: str
    before_json: str | None
    after_json: str | None
    note: str | None
    operator_label: str
    created_at: datetime


class FieldVerificationCreate(ORMModel):
    developer_id: int | None = None
    project_id: int | None = None
    field_name: str = Field(max_length=100)
    verified_value: str = Field(min_length=1, max_length=2048)
    verification_status: Literal["verified", "rejected", "needs_review"]
    source_evidence_id: int | None = None
    review_note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_owner(self) -> "FieldVerificationCreate":
        if (self.developer_id is None) == (self.project_id is None):
            raise ValueError("exactly one owner is required")
        return self


class FieldVerificationRead(FieldVerificationCreate):
    id: int
    verified_at: datetime
    created_at: datetime
    updated_at: datetime


class OutreachActivityCreate(ORMModel):
    developer_id: int | None = None
    project_id: int | None = None
    activity_type: str = Field(max_length=50)
    channel: str = Field(max_length=50)
    direction: str = Field(max_length=50)
    status_after: str | None = Field(default=None, max_length=50)
    contact_value: str | None = Field(default=None, max_length=2048)
    contact_person: str | None = Field(default=None, max_length=255)
    note: str | None = Field(default=None, max_length=5000)
    follow_up_at: datetime | None = None
    occurred_at: datetime | None = None

    @model_validator(mode="after")
    def validate_owner(self) -> "OutreachActivityCreate":
        if (self.developer_id is None) == (self.project_id is None):
            raise ValueError("exactly one owner is required")
        return self


class OutreachActivityUpdate(ORMModel):
    activity_type: str | None = Field(default=None, max_length=50)
    channel: str | None = Field(default=None, max_length=50)
    direction: str | None = Field(default=None, max_length=50)
    status_after: str | None = Field(default=None, max_length=50)
    contact_value: str | None = Field(default=None, max_length=2048)
    contact_person: str | None = Field(default=None, max_length=255)
    note: str | None = Field(default=None, max_length=5000)
    follow_up_at: datetime | None = None
    occurred_at: datetime | None = None


class OutreachActivityRead(ORMModel):
    id: int
    developer_id: int | None
    project_id: int | None
    activity_type: str
    channel: str
    direction: str
    status_after: str | None
    contact_value: str | None
    contact_person: str | None
    note: str | None
    follow_up_at: datetime | None
    occurred_at: datetime
    created_at: datetime
    updated_at: datetime


class BulkActionRequest(ORMModel):
    entity_type: Literal["project", "developer"]
    entity_ids: list[int] = Field(min_length=1, max_length=100)
    action: Literal["set_review_status", "set_outreach_status", "add_review_note", "exclude"]
    payload: dict[str, Any]


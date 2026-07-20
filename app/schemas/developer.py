from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.schemas.common import LongText, NameStr, ORMModel, UrlStr


class DeveloperBase(ORMModel):
    name: NameStr
    legal_name: str | None = Field(default=None, max_length=255)
    description: LongText | None = None
    classification: str = Field(default="uncertain", max_length=50)
    verification_status: str = Field(default="unverified", max_length=50)
    review_status: str = Field(default="unreviewed", max_length=50)
    review_note: LongText | None = None
    outreach_status: str = Field(default="not_contacted", max_length=50)
    next_follow_up_at: datetime | None = None
    website_url: UrlStr | None = None
    office_address: LongText | None = None
    city: str = Field(default="Lahore", max_length=100)
    country: str = Field(default="Pakistan", max_length=100)


class DeveloperCreate(DeveloperBase):
    pass


class DeveloperUpdate(ORMModel):
    expected_version: int | None = Field(default=None, ge=1)
    name: NameStr | None = None
    legal_name: str | None = Field(default=None, max_length=255)
    description: LongText | None = None
    classification: str | None = Field(default=None, max_length=50)
    verification_status: str | None = Field(default=None, max_length=50)
    review_status: str | None = Field(default=None, max_length=50)
    review_note: LongText | None = None
    outreach_status: str | None = Field(default=None, max_length=50)
    next_follow_up_at: datetime | None = None
    website_url: UrlStr | None = None
    office_address: LongText | None = None
    city: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)


class DeveloperRead(DeveloperBase):
    id: int
    normalized_name: str | None
    created_at: datetime
    updated_at: datetime
    record_status: str = "active"
    merged_into_developer_id: int | None = None
    merged_at: datetime | None = None
    last_reviewed_at: datetime | None = None
    last_outreach_at: datetime | None = None
    version_number: int = 1


class DeveloperMutationResponse(ORMModel):
    item: DeveloperRead
    changed_fields: list[str]
    review_event_id: int | None = None


class DeveloperReviewRequest(ORMModel):
    review_status: str = Field(max_length=50)
    review_note: str | None = Field(default=None, max_length=2000)
    expected_version: int = Field(ge=1)


class DeveloperWithProjects(DeveloperRead):
    projects: list["ProjectRead"] = []


from app.schemas.project import ProjectRead

DeveloperWithProjects.model_rebuild()

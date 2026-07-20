from __future__ import annotations

from datetime import datetime

from pydantic import Field, field_validator

from app.schemas.common import LongText, NameStr, ORMModel, UrlStr


class ProjectBase(ORMModel):
    developer_id: int | None = None
    name: NameStr
    description: LongText | None = None
    project_type: str | None = Field(default=None, max_length=100)
    project_status: str = Field(default="unknown", max_length=50)
    verification_status: str = Field(default="unverified", max_length=50)
    review_status: str = Field(default="unreviewed", max_length=50)
    review_note: LongText | None = None
    outreach_status: str = Field(default="not_contacted", max_length=50)
    next_follow_up_at: datetime | None = None
    address: LongText | None = None
    lahore_zone: str | None = Field(default=None, max_length=150)
    city: str = Field(default="Lahore", max_length=100)
    country: str = Field(default="Pakistan", max_length=100)
    latitude: float | None = None
    longitude: float | None = None
    google_place_id: str | None = Field(default=None, max_length=255)
    google_maps_url: UrlStr | None = None
    official_website_url: UrlStr | None = None

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, value: float | None) -> float | None:
        if value is not None and not -90 <= value <= 90:
            raise ValueError("latitude must be between -90 and 90")
        return value

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, value: float | None) -> float | None:
        if value is not None and not -180 <= value <= 180:
            raise ValueError("longitude must be between -180 and 180")
        return value


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(ORMModel):
    expected_version: int | None = Field(default=None, ge=1)
    developer_id: int | None = None
    name: NameStr | None = None
    description: LongText | None = None
    project_type: str | None = Field(default=None, max_length=100)
    project_status: str | None = Field(default=None, max_length=50)
    verification_status: str | None = Field(default=None, max_length=50)
    review_status: str | None = Field(default=None, max_length=50)
    review_note: LongText | None = None
    outreach_status: str | None = Field(default=None, max_length=50)
    next_follow_up_at: datetime | None = None
    address: LongText | None = None
    lahore_zone: str | None = Field(default=None, max_length=150)
    city: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)
    latitude: float | None = None
    longitude: float | None = None
    google_place_id: str | None = Field(default=None, max_length=255)
    google_maps_url: UrlStr | None = None
    official_website_url: UrlStr | None = None

    _validate_latitude = field_validator("latitude")(ProjectBase.validate_latitude.__func__)
    _validate_longitude = field_validator("longitude")(ProjectBase.validate_longitude.__func__)


class ProjectRead(ProjectBase):
    id: int
    normalized_name: str | None
    created_at: datetime
    updated_at: datetime
    record_status: str = "active"
    merged_into_project_id: int | None = None
    merged_at: datetime | None = None
    last_reviewed_at: datetime | None = None
    last_outreach_at: datetime | None = None
    version_number: int = 1


class ProjectMutationResponse(ORMModel):
    item: ProjectRead
    changed_fields: list[str]
    review_event_id: int | None = None


class ProjectReviewRequest(ORMModel):
    review_status: str = Field(max_length=50)
    review_note: str | None = Field(default=None, max_length=2000)
    expected_version: int = Field(ge=1)

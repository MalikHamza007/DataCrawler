from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from app.schemas.common import CapturedText, ORMModel, UrlStr

SourceType = Literal[
    "manual",
    "official_website",
    "project_website",
    "google_places",
    "google_maps",
    "facebook",
    "instagram",
    "x",
    "linkedin",
    "youtube",
    "meta_ad_library",
    "news",
    "directory",
    "other",
]


class SourceEvidenceBase(ORMModel):
    developer_id: int | None = None
    project_id: int | None = None
    collection_job_id: int | None = None
    source_type: SourceType
    source_url: UrlStr
    source_title: str | None = Field(default=None, max_length=255)
    captured_text: CapturedText | None = None
    field_name: str | None = Field(default=None, max_length=255)
    extracted_value: str | None = Field(default=None, max_length=2048)
    verification_status: str = Field(default="unverified", max_length=50)

    @model_validator(mode="after")
    def validate_owner(self) -> "SourceEvidenceBase":
        if self.developer_id is None and self.project_id is None and self.collection_job_id is None:
            raise ValueError("at least one of developer_id, project_id, or collection_job_id is required")
        return self


class SourceEvidenceCreate(SourceEvidenceBase):
    pass


class SourceEvidenceUpdate(ORMModel):
    source_type: SourceType | None = None
    source_url: UrlStr | None = None
    source_title: str | None = Field(default=None, max_length=255)
    captured_text: CapturedText | None = None
    field_name: str | None = Field(default=None, max_length=255)
    extracted_value: str | None = Field(default=None, max_length=2048)
    verification_status: str | None = Field(default=None, max_length=50)


class SourceEvidenceRead(SourceEvidenceBase):
    id: int
    collected_at: datetime
    created_at: datetime

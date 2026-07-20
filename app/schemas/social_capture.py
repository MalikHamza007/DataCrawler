from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import ConfigDict, Field, field_validator, model_validator

from app.schemas.common import ORMModel, UrlStr

CapturePlatform = Literal["facebook", "instagram", "x", "linkedin", "meta_ad_library", "generic"]
CapturePageKind = Literal[
    "business_profile",
    "company_page",
    "project_page",
    "public_post",
    "promotional_post",
    "ad_library_result",
    "search_result_page",
    "unknown_public_page",
]
ReviewStatus = Literal["unassigned", "attached", "review_required", "accepted", "rejected", "duplicate"]


class CaptureContact(ORMModel):
    value: str = Field(min_length=1, max_length=2048)
    label: str | None = Field(default=None, max_length=255)
    url: UrlStr | None = None


class CampaignPayload(ORMModel):
    campaign_type: Literal["meta_ad_library", "public_promotional_post", "public_project_post", "other_public_campaign_evidence"]
    advertiser_name: str | None = Field(default=None, max_length=255)
    campaign_text: str | None = Field(default=None, max_length=10000)
    call_to_action: str | None = Field(default=None, max_length=255)
    destination_url: UrlStr | None = None
    visible_status: Literal["active_visible", "inactive_visible", "status_not_visible", "unknown"] = "unknown"
    verification_status: Literal["captured_from_ad_library", "public_post_only", "operator_verified", "unverified", "rejected"] = "unverified"


class CaptureContract(ORMModel):
    model_config = ConfigDict(extra="forbid")

    capture_version: Literal["1"]
    platform: CapturePlatform
    page_kind: CapturePageKind
    source_url: UrlStr
    canonical_url: UrlStr | None = None
    page_title: str | None = Field(default=None, max_length=255)
    profile_name: str | None = Field(default=None, max_length=255)
    username: str | None = Field(default=None, max_length=255)
    visible_text_excerpt: str | None = Field(default=None, max_length=20000)
    about_text: str | None = Field(default=None, max_length=10000)
    project_names: list[str] = Field(default_factory=list, max_length=50)
    phones: list[CaptureContact] = Field(default_factory=list, max_length=30)
    emails: list[CaptureContact] = Field(default_factory=list, max_length=30)
    whatsapp: list[CaptureContact] = Field(default_factory=list, max_length=30)
    addresses: list[str] = Field(default_factory=list, max_length=20)
    websites: list[UrlStr] = Field(default_factory=list, max_length=30)
    external_links: list[UrlStr] = Field(default_factory=list, max_length=100)
    campaign: CampaignPayload | None = None
    captured_at: datetime
    extractor_version: str = Field(min_length=1, max_length=80)
    warnings: list[str] = Field(default_factory=list, max_length=50)

    @field_validator("project_names", "addresses", "warnings")
    @classmethod
    def trim_string_arrays(cls, values: list[str]) -> list[str]:
        return [value.strip()[:2048] for value in values if value and value.strip()]


class SubmittedField(ORMModel):
    field_name: str = Field(min_length=1, max_length=100)
    source_label: str | None = Field(default=None, max_length=255)
    original_extracted_value: str = Field(min_length=1, max_length=2048)
    submitted_value: str = Field(min_length=1, max_length=2048)
    include: bool = True
    target_entity: Literal["developer", "project", "both", "capture"] = "both"

    @property
    def was_edited(self) -> bool:
        return self.original_extracted_value.strip() != self.submitted_value.strip()


class SocialCaptureCreate(ORMModel):
    model_config = ConfigDict(extra="forbid")

    capture: CaptureContract
    selected_fields: list[SubmittedField] = Field(default_factory=list, max_length=250)
    developer_id: int | None = None
    project_id: int | None = None
    extension_version: str | None = Field(default=None, max_length=50)
    operator_note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def require_supported_page(self) -> "SocialCaptureCreate":
        if self.capture.page_kind == "search_result_page":
            raise ValueError("Open one business or project result before capturing. Bulk search-result collection is not supported.")
        return self


class SocialCaptureRead(ORMModel):
    id: int
    platform: str
    page_kind: str
    source_url: str
    canonical_url: str | None
    page_title: str | None
    profile_name: str | None
    username: str | None
    visible_text_excerpt: str | None
    about_text: str | None
    capture_payload_json: str
    content_hash: str
    extractor_version: str
    capture_version: str
    extension_version: str | None
    developer_id: int | None
    project_id: int | None
    review_status: str
    captured_at: datetime
    received_at: datetime
    reviewed_at: datetime | None
    review_note: str | None
    created_at: datetime
    updated_at: datetime


class SocialCaptureResponse(ORMModel):
    id: int
    status: str
    developer_id: int | None
    project_id: int | None
    source_evidence_created: int
    contacts_created: int
    social_profiles_created: int
    campaign_evidence_created: int
    warnings: list[str] = Field(default_factory=list)


class SocialCaptureDuplicate(ORMModel):
    existing_capture_id: int
    status: str = "duplicate"
    message: str = "Duplicate capture already exists."


class CaptureAttachRequest(ORMModel):
    developer_id: int | None = None
    project_id: int | None = None
    create_evidence: bool = True
    review_note: str | None = Field(default=None, max_length=2000)


class CaptureReviewRequest(ORMModel):
    review_note: str | None = Field(default=None, max_length=2000)


class SocialCapturePatch(ORMModel):
    review_status: ReviewStatus | None = None
    review_note: str | None = Field(default=None, max_length=2000)


class EntitySearchItem(ORMModel):
    entity_type: Literal["developer", "project"]
    id: int
    name: str
    subtitle: str | None = None
    classification: str | None = None
    record_status: str


class EntitySearchResponse(ORMModel):
    items: list[EntitySearchItem]


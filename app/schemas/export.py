from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


ExportFormat = Literal["xlsx", "csv", "json"]
ExportScope = Literal[
    "current_project_view",
    "current_developer_view",
    "all_projects",
    "refined_projects",
    "all_developers",
    "full_intelligence",
    "review_queue",
    "outreach_pipeline",
]
ExportStatus = Literal["queued", "generating", "validating", "ready", "failed", "cancelled", "deleted", "expired"]

PROJECT_FILTER_KEYS = {
    "q",
    "developer_id",
    "developer_assignment",
    "lahore_zone",
    "project_type",
    "project_status",
    "classification",
    "verification_status",
    "review_status",
    "outreach_status",
    "record_status",
    "minimum_classification_score",
    "maximum_classification_score",
    "has_phone",
    "has_whatsapp",
    "has_email",
    "has_website",
    "has_social_profile",
    "has_campaign_evidence",
    "has_coordinates",
    "has_pending_duplicate",
    "has_pending_relationship",
    "source_type",
    "collection_job_id",
    "created_after",
    "created_before",
    "updated_after",
    "updated_before",
    "map_north",
    "map_south",
    "map_east",
    "map_west",
    "include_merged",
}
DEVELOPER_FILTER_KEYS = {
    "q",
    "classification",
    "verification_status",
    "review_status",
    "outreach_status",
    "record_status",
    "minimum_classification_score",
    "maximum_classification_score",
    "has_phone",
    "has_whatsapp",
    "has_email",
    "has_website",
    "has_social_profile",
    "has_projects",
    "has_lahore_projects",
    "has_pending_duplicate",
    "created_after",
    "created_before",
    "updated_after",
    "updated_before",
    "include_merged",
}


class ExportOptions(BaseModel):
    include_contacts: bool = True
    include_social_profiles: bool = True
    include_campaign_evidence: bool = True
    include_source_evidence: bool = False
    include_relationships: bool = True
    include_duplicate_candidates: bool = True
    include_outreach_activities: bool = True
    include_collection_logs: bool = False
    include_rejected_records: bool = False
    include_excluded_records: bool = False
    include_merged_records: bool = False
    include_unassigned_projects: bool = True
    include_unassigned_social_captures: bool = False

    model_config = ConfigDict(extra="forbid")


class ExportBaseRequest(BaseModel):
    format: ExportFormat
    scope: ExportScope
    project_filters: dict[str, Any] = Field(default_factory=dict)
    developer_filters: dict[str, Any] = Field(default_factory=dict)
    options: ExportOptions = Field(default_factory=ExportOptions)

    model_config = ConfigDict(extra="forbid")

    @field_validator("project_filters")
    @classmethod
    def validate_project_filters(cls, value: dict[str, Any]) -> dict[str, Any]:
        unknown = set(value) - PROJECT_FILTER_KEYS
        if unknown:
            raise ValueError(f"Unknown project filters: {', '.join(sorted(unknown))}")
        return value

    @field_validator("developer_filters")
    @classmethod
    def validate_developer_filters(cls, value: dict[str, Any]) -> dict[str, Any]:
        unknown = set(value) - DEVELOPER_FILTER_KEYS
        if unknown:
            raise ValueError(f"Unknown developer filters: {', '.join(sorted(unknown))}")
        return value

    @model_validator(mode="after")
    def apply_scope_defaults(self) -> "ExportBaseRequest":
        if self.scope == "full_intelligence":
            self.options.include_source_evidence = self.options.include_source_evidence
        return self


class ExportPreviewRequest(ExportBaseRequest):
    pass


class ExportCreateRequest(ExportBaseRequest):
    filename_label: str | None = Field(default=None, max_length=120)


class ExportEstimatedCounts(BaseModel):
    projects: int = 0
    developers: int = 0
    project_contacts: int = 0
    developer_contacts: int = 0
    social_profiles: int = 0
    campaign_evidence: int = 0
    source_evidence: int = 0
    relationships: int = 0
    duplicate_candidates: int = 0
    outreach_activities: int = 0
    social_captures: int = 0
    collection_logs: int = 0


class ExportPreviewResponse(BaseModel):
    scope: ExportScope
    format: ExportFormat
    estimated: ExportEstimatedCounts
    estimated_primary_rows: int
    within_row_limit: bool
    warnings: list[str] = []


class ExportArtifactRead(BaseModel):
    id: int
    collection_job_id: int
    format: ExportFormat
    scope: ExportScope
    status: ExportStatus
    filename: str
    media_type: str
    row_count: int | None = None
    file_size_bytes: int | None = None
    sha256: str | None = None
    generated_at: datetime | None = None
    expires_at: datetime | None = None
    download_count: int = 0
    last_downloaded_at: datetime | None = None
    error_message: str | None = None
    summary: dict[str, Any] = Field(default_factory=dict)
    filter_snapshot: dict[str, Any] = Field(default_factory=dict)
    options: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExportListResponse(BaseModel):
    items: list[ExportArtifactRead]
    pagination: dict[str, Any]

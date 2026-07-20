from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field
from pydantic import model_validator

from app.schemas.common import LongText, ORMModel
from app.schemas.map_config import ProjectSearchConfig

JobType = Literal["places_discovery", "website_enrichment", "classification_analysis", "duplicate_scan", "export_generation", "social_capture", "export", "manual_research"]
JobStatus = Literal["queued", "running", "completed", "failed", "cancelled"]
LogLevel = Literal["debug", "info", "warning", "error"]


class CollectionJobBase(ORMModel):
    job_type: JobType
    city: str = Field(default="Lahore", max_length=100)
    lahore_zone: str | None = Field(default=None, max_length=150)
    search_config_json: dict | None = None


class CollectionJobCreate(CollectionJobBase):
    @model_validator(mode="after")
    def validate_places_discovery_config(self) -> "CollectionJobCreate":
        if self.job_type == "places_discovery":
            ProjectSearchConfig.model_validate(self.search_config_json)
        return self


class CollectionJobUpdate(ORMModel):
    status: JobStatus | None = None
    total_items: int | None = Field(default=None, ge=0)
    processed_items: int | None = Field(default=None, ge=0)
    created_items: int | None = Field(default=None, ge=0)
    updated_items: int | None = Field(default=None, ge=0)
    failed_items: int | None = Field(default=None, ge=0)
    error_message: LongText | None = None


class CollectionLogCreate(ORMModel):
    level: LogLevel = "info"
    message: str = Field(min_length=1, max_length=10000)
    context_json: dict | None = None


class CollectionLogRead(CollectionLogCreate):
    id: int
    collection_job_id: int
    created_at: datetime


class CollectionJobRead(CollectionJobBase):
    id: int
    status: JobStatus
    total_items: int
    processed_items: int
    created_items: int
    updated_items: int
    failed_items: int
    error_message: str | None
    worker_id: str | None = None
    claimed_at: datetime | None = None
    heartbeat_at: datetime | None = None
    lease_expires_at: datetime | None = None
    cancel_requested_at: datetime | None = None
    attempt_count: int = 0
    max_attempts: int = 3
    next_attempt_at: datetime | None = None
    progress_phase: str = "queued"
    progress_message: str | None = None
    last_error_type: str | None = None
    last_error_retryable: bool | None = None
    execution_summary_json: dict | None = None
    progress_percent: int = 0
    is_cancellable: bool = False
    is_retryable: bool = False
    worker_active: bool = False
    website_crawl_id: int | None = None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    logs: list[CollectionLogRead] = []

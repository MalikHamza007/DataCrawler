from datetime import datetime

from app.schemas.common import ORMModel


class WebsiteCrawlRead(ORMModel):
    id: int
    collection_job_id: int
    project_id: int | None
    developer_id: int | None
    seed_url: str
    canonical_seed_url: str
    registered_domain: str
    crawl_mode: str
    status: str
    robots_status: str | None
    robots_url: str | None
    pages_discovered: int
    pages_queued: int
    pages_fetched: int
    pages_skipped: int
    pages_failed: int
    playwright_pages: int
    projects_discovered: int
    developers_discovered: int
    contacts_discovered: int
    social_profiles_discovered: int
    warning_message: str | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class WebsitePageRead(ORMModel):
    id: int
    website_crawl_id: int
    url: str
    canonical_url: str
    parent_url: str | None
    depth: int
    priority_score: int
    status: str
    http_status: int | None
    content_type: str | None
    fetch_method: str | None
    title: str | None
    meta_description: str | None
    canonical_tag: str | None
    content_hash: str | None
    text_length: int
    word_count: int
    fetched_at: datetime | None
    error_type: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

CrawlMode = Literal["project_site", "developer_site", "unknown_official_site"]


class WebsiteEnrichmentRequest(BaseModel):
    seed_url: str = Field(min_length=1, max_length=2048)
    max_pages: int | None = Field(default=None, ge=1, le=200)
    use_playwright_fallback: bool = True
    allow_subdomains: bool | None = None
    crawl_mode: CrawlMode = "unknown_official_site"


class ManualWebsiteEnrichmentRequest(WebsiteEnrichmentRequest):
    project_id: int | None = None
    developer_id: int | None = None

    @model_validator(mode="after")
    def validate_owner(self) -> "ManualWebsiteEnrichmentRequest":
        if self.project_id is not None and self.developer_id is not None:
            raise ValueError("A website job cannot have both project and developer owners")
        return self


class WebsitePreviewRequest(BaseModel):
    seed_url: str = Field(min_length=1, max_length=2048)
    crawl_mode: CrawlMode = "unknown_official_site"


class WebsitePreviewResponse(BaseModel):
    canonical_seed_url: str
    registered_domain: str
    robots_url: str
    allowed_scheme: bool
    ssrf_check: str
    estimated_limits: dict[str, int]

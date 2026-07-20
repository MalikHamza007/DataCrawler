from __future__ import annotations

from pydantic import BaseModel


class PlacesStatusRead(BaseModel):
    enabled: bool
    configured: bool
    dry_run: bool
    text_search_available: bool
    nearby_search_available: bool
    details_enrichment_enabled: bool


class SearchPlanQueryRead(BaseModel):
    query: str
    cell_id: str


class SearchPlanRead(BaseModel):
    job_id: int
    search_mode: str
    cell_count: int
    query_count: int
    nearby_request_count: int
    estimated_max_pages: int
    estimated_max_requests: int
    estimated_max_results: int
    selected_project_types: list[str]
    queries: list[SearchPlanQueryRead]


class PlacesDiscoveryResult(BaseModel):
    job_id: int
    status: str
    requests_made: int
    retry_count: int
    raw_results: int
    unique_place_ids: int
    projects_created: int
    projects_updated: int
    contacts_created: int
    websites_discovered: int
    duplicates_skipped: int
    results_outside_geometry: int
    dry_run: bool = False

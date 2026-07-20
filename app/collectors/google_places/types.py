from __future__ import annotations

from dataclasses import dataclass, field

from app.schemas.map_config import MapBounds, MapPoint


@dataclass(frozen=True)
class SearchCell:
    id: str
    bounds: MapBounds
    center: MapPoint
    radius_meters: int


@dataclass(frozen=True)
class QuerySpec:
    query: str
    project_type: str
    cell_id: str
    location_restriction: dict


@dataclass(frozen=True)
class NearbySpec:
    included_type: str
    project_type: str
    cell_id: str
    center: MapPoint
    radius_meters: int


@dataclass
class SearchPlan:
    job_id: int
    search_mode: str
    selected_project_types: list[str]
    cells: list[SearchCell]
    queries: list[QuerySpec]
    nearby_specs: list[NearbySpec] = field(default_factory=list)
    estimated_max_pages: int = 0
    estimated_max_requests: int = 0
    estimated_max_results: int = 0


@dataclass(frozen=True)
class NormalizedPlaceCandidate:
    google_place_id: str
    display_name: str
    formatted_address: str | None
    latitude: float | None
    longitude: float | None
    primary_type: str | None
    types: list[str]
    business_status: str | None
    google_maps_url: str | None
    website_url: str | None
    national_phone_number: str | None
    international_phone_number: str | None
    source_method: str
    source_query: str | None
    source_cell_id: str | None

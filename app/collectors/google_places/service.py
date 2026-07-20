from __future__ import annotations

from app.collectors.google_places.geometry import generate_cells_for_config
from app.collectors.google_places.query_generator import build_nearby_specs, build_query_specs
from app.collectors.google_places.types import SearchPlan
from app.core.config import Settings, get_settings
from app.schemas.map_config import ProjectSearchConfig


def build_search_plan(job_id: int, config: ProjectSearchConfig, settings: Settings | None = None) -> SearchPlan:
    settings = settings or get_settings()
    cells = generate_cells_for_config(
        config,
        cell_radius_meters=settings.places_grid_cell_radius_meters,
        max_cells=settings.places_grid_max_cells,
    )
    queries = build_query_specs(config, cells, max_queries=settings.google_places_max_queries_per_job)
    nearby_specs = build_nearby_specs(config, cells) if settings.google_places_enable_nearby_search else []
    estimated_max_pages = len(queries) * settings.google_places_max_pages_per_query
    estimated_max_requests = estimated_max_pages + len(nearby_specs)
    if len(queries) > settings.google_places_max_queries_per_job:
        raise ValueError("Search plan exceeds maximum query count.")
    if estimated_max_requests > settings.google_places_max_queries_per_job * settings.google_places_max_pages_per_query + len(nearby_specs):
        raise ValueError("Search plan exceeds request limits.")
    return SearchPlan(
        job_id=job_id,
        search_mode=config.search_mode,
        selected_project_types=config.project_types,
        cells=cells,
        queries=queries,
        nearby_specs=nearby_specs,
        estimated_max_pages=estimated_max_pages,
        estimated_max_requests=estimated_max_requests,
        estimated_max_results=settings.google_places_max_results_per_job,
    )

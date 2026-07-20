from __future__ import annotations

from app.collectors.google_places.constants import GENERIC_QUERY, NEARBY_TYPE_MAPPINGS, QUERY_TEMPLATES
from app.collectors.google_places.geometry import bounds_to_google_rectangle
from app.collectors.google_places.types import NearbySpec, QuerySpec, SearchCell
from app.schemas.map_config import ProjectSearchConfig
from app.services.lahore_zones import get_zone


def zone_label(config: ProjectSearchConfig) -> str:
    if config.zone_id:
        zone = get_zone(config.zone_id)
        if zone is not None:
            return zone.name
    return "Lahore"


def generate_project_queries(config: ProjectSearchConfig, *, max_queries: int) -> list[tuple[str, str]]:
    zone = zone_label(config)
    seen: set[str] = set()
    ordered: list[tuple[str, str]] = []
    max_template_count = max(len(QUERY_TEMPLATES.get(project_type, [])) for project_type in config.project_types)
    for index in range(max_template_count):
        for project_type in config.project_types:
            templates = QUERY_TEMPLATES.get(project_type, QUERY_TEMPLATES["other"])
            if index >= len(templates):
                continue
            query = templates[index].format(zone=zone)
            if "Lahore" not in query:
                query = f"{query} Lahore"
            if query not in seen:
                seen.add(query)
                ordered.append((query, project_type))
            if len(ordered) >= max_queries:
                return ordered
    fallback = GENERIC_QUERY.format(zone=zone)
    if fallback not in seen and len(ordered) < max_queries:
        ordered.append((fallback, "other"))
    return ordered


def build_query_specs(config: ProjectSearchConfig, cells: list[SearchCell], *, max_queries: int) -> list[QuerySpec]:
    base_queries = generate_project_queries(config, max_queries=max_queries)
    specs: list[QuerySpec] = []
    for cell in cells:
        for query, project_type in base_queries:
            specs.append(QuerySpec(query=query, project_type=project_type, cell_id=cell.id, location_restriction=bounds_to_google_rectangle(cell.bounds)))
            if len(specs) >= max_queries:
                return specs
    return specs


def build_nearby_specs(config: ProjectSearchConfig, cells: list[SearchCell]) -> list[NearbySpec]:
    specs: list[NearbySpec] = []
    for project_type in config.project_types:
        for included_type in NEARBY_TYPE_MAPPINGS.get(project_type, []):
            for cell in cells:
                specs.append(
                    NearbySpec(
                        included_type=included_type,
                        project_type=project_type,
                        cell_id=cell.id,
                        center=cell.center,
                        radius_meters=min(cell.radius_meters, 50_000),
                    )
                )
    return specs

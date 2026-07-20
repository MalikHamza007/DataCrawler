from __future__ import annotations

import math

from app.collectors.google_places.exceptions import SearchGeometryError
from app.collectors.google_places.types import SearchCell
from app.schemas.map_config import MapBounds, MapPoint, ProjectSearchConfig
from app.services.lahore_zones import LAHORE_SERVICE_BOUNDARY, get_zone

METERS_PER_DEGREE_LAT = 111_320


def bounds_to_google_rectangle(bounds: MapBounds) -> dict:
    validate_bounds(bounds)
    return {
        "rectangle": {
            "low": {"latitude": bounds.south, "longitude": bounds.west},
            "high": {"latitude": bounds.north, "longitude": bounds.east},
        }
    }


def circle_to_google_restriction(center: MapPoint, radius_meters: int) -> dict:
    if radius_meters <= 0 or radius_meters > 50_000:
        raise SearchGeometryError("Nearby Search radius must be between 1 and 50000 metres.")
    return {"circle": {"center": {"latitude": center.lat, "longitude": center.lng}, "radius": radius_meters}}


def radius_to_bounds(center: MapPoint, radius_meters: int) -> MapBounds:
    lat_delta = radius_meters / METERS_PER_DEGREE_LAT
    lng_delta = radius_meters / (METERS_PER_DEGREE_LAT * max(math.cos(math.radians(center.lat)), 0.2))
    return MapBounds(north=center.lat + lat_delta, south=center.lat - lat_delta, east=center.lng + lng_delta, west=center.lng - lng_delta)


def point_in_bounds(point: MapPoint, bounds: MapBounds) -> bool:
    return bounds.south <= point.lat <= bounds.north and bounds.west <= point.lng <= bounds.east


def point_in_polygon(point: MapPoint, polygon: list[MapPoint]) -> bool:
    inside = False
    j = len(polygon) - 1
    for i, current in enumerate(polygon):
        previous = polygon[j]
        intersects = ((current.lng > point.lng) != (previous.lng > point.lng)) and (
            point.lat
            < (previous.lat - current.lat) * (point.lng - current.lng) / ((previous.lng - current.lng) or 1e-12)
            + current.lat
        )
        if intersects:
            inside = not inside
        j = i
    return inside


def polygon_bounds(points: list[MapPoint]) -> MapBounds:
    if len(points) < 3:
        raise SearchGeometryError("Polygon must contain at least three points.")
    return MapBounds(
        north=max(point.lat for point in points),
        south=min(point.lat for point in points),
        east=max(point.lng for point in points),
        west=min(point.lng for point in points),
    )


def generate_cells_for_config(config: ProjectSearchConfig, *, cell_radius_meters: int, max_cells: int) -> list[SearchCell]:
    if config.search_mode == "zone":
        zone = get_zone(config.zone_id or "")
        if zone is None:
            raise SearchGeometryError("Unknown Lahore zone.")
        bounds = zone.bounds or radius_to_bounds(zone.center, config.radius_meters or 5000)
        return generate_cells(bounds, cell_radius_meters=cell_radius_meters, max_cells=max_cells, prefix=zone.id)
    if config.search_mode == "radius":
        if config.map_center is None or config.radius_meters is None:
            raise SearchGeometryError("Radius mode requires center and radius.")
        bounds = radius_to_bounds(config.map_center, config.radius_meters)
        return [SearchCell(id="radius-001", bounds=bounds, center=config.map_center, radius_meters=config.radius_meters)]
    if config.search_mode == "rectangle":
        assert config.geometry is not None
        bounds = MapBounds(
            north=config.geometry.north,
            south=config.geometry.south,
            east=config.geometry.east,
            west=config.geometry.west,
        )
        return generate_cells(bounds, cell_radius_meters=cell_radius_meters, max_cells=max_cells, prefix="rectangle")
    if config.search_mode == "polygon":
        assert config.geometry is not None and config.geometry.coordinates is not None
        bounds = polygon_bounds(config.geometry.coordinates)
        return generate_cells(bounds, cell_radius_meters=cell_radius_meters, max_cells=max_cells, prefix="polygon")
    raise SearchGeometryError("Unsupported search mode.")


def generate_cells(bounds: MapBounds, *, cell_radius_meters: int, max_cells: int, prefix: str) -> list[SearchCell]:
    validate_bounds(bounds)
    if cell_radius_meters <= 0:
        raise SearchGeometryError("Cell radius must be positive.")
    lat_step = (cell_radius_meters * 2) / METERS_PER_DEGREE_LAT
    mid_lat = (bounds.north + bounds.south) / 2
    lng_step = (cell_radius_meters * 2) / (METERS_PER_DEGREE_LAT * max(math.cos(math.radians(mid_lat)), 0.2))
    rows = max(1, math.ceil((bounds.north - bounds.south) / lat_step))
    cols = max(1, math.ceil((bounds.east - bounds.west) / lng_step))
    count = rows * cols
    if count > max_cells:
        raise SearchGeometryError(f"Search area would create {count} cells, above limit {max_cells}.")

    cells: list[SearchCell] = []
    lat_height = (bounds.north - bounds.south) / rows
    lng_width = (bounds.east - bounds.west) / cols
    for row in range(rows):
        for col in range(cols):
            south = bounds.south + row * lat_height
            north = bounds.south + (row + 1) * lat_height
            west = bounds.west + col * lng_width
            east = bounds.west + (col + 1) * lng_width
            cell_bounds = MapBounds(north=north, south=south, east=east, west=west)
            cells.append(
                SearchCell(
                    id=f"{prefix}-{len(cells) + 1:03d}",
                    bounds=cell_bounds,
                    center=MapPoint(lat=(north + south) / 2, lng=(east + west) / 2),
                    radius_meters=cell_radius_meters,
                )
            )
    return cells


def validate_bounds(bounds: MapBounds) -> None:
    if bounds.north <= bounds.south or bounds.east <= bounds.west:
        raise SearchGeometryError("Invalid bounds.")
    corners = [
        MapPoint(lat=bounds.north, lng=bounds.east),
        MapPoint(lat=bounds.north, lng=bounds.west),
        MapPoint(lat=bounds.south, lng=bounds.east),
        MapPoint(lat=bounds.south, lng=bounds.west),
    ]
    if not all(point_in_bounds(point, LAHORE_SERVICE_BOUNDARY) for point in corners):
        raise SearchGeometryError("Bounds fall outside Lahore service boundary.")

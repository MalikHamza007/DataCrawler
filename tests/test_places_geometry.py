import pytest

from app.collectors.google_places.geometry import bounds_to_google_rectangle, generate_cells_for_config, point_in_polygon, radius_to_bounds
from app.collectors.google_places.exceptions import SearchGeometryError
from app.schemas.map_config import MapBounds, MapPoint, ProjectSearchConfig, SearchGeometry


def test_rectangle_to_google_viewport() -> None:
    bounds = MapBounds(north=31.54, south=31.49, east=74.38, west=74.32)
    viewport = bounds_to_google_rectangle(bounds)
    assert viewport["rectangle"]["low"] == {"latitude": 31.49, "longitude": 74.32}
    assert viewport["rectangle"]["high"] == {"latitude": 31.54, "longitude": 74.38}


def test_radius_creates_valid_bounds() -> None:
    bounds = radius_to_bounds(MapPoint(lat=31.5204, lng=74.3587), 5000)
    assert bounds.north > bounds.south
    assert bounds.east > bounds.west


def test_polygon_cells_and_point_filter_are_deterministic() -> None:
    points = [MapPoint(lat=31.52, lng=74.33), MapPoint(lat=31.54, lng=74.36), MapPoint(lat=31.50, lng=74.39)]
    config = ProjectSearchConfig(search_mode="polygon", project_types=["apartments"], geometry=SearchGeometry(type="polygon", coordinates=points))
    cells = generate_cells_for_config(config, cell_radius_meters=3000, max_cells=100)
    assert [cell.id for cell in cells] == [cell.id for cell in generate_cells_for_config(config, cell_radius_meters=3000, max_cells=100)]
    assert cells
    assert point_in_polygon(MapPoint(lat=31.52, lng=74.36), points)
    assert not point_in_polygon(MapPoint(lat=31.60, lng=74.36), points)


def test_invalid_or_excessive_cells_rejected() -> None:
    config = ProjectSearchConfig(search_mode="zone", zone_id="all_lahore", radius_meters=5000, project_types=["apartments"])
    with pytest.raises(SearchGeometryError):
        generate_cells_for_config(config, cell_radius_meters=500, max_cells=5)

    with pytest.raises(ValueError):
        MapBounds(north=31.0, south=31.5, east=74.5, west=74.1)

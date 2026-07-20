from __future__ import annotations

from app.core.exceptions import InvalidOwnerError
from app.core.config import get_settings
from app.schemas.map_config import LahoreZone, MapBounds, MapConfigRead, MapPoint, ProjectSearchConfig, ProjectTypeOption

LAHORE_CENTER = MapPoint(lat=31.5204, lng=74.3587)
LAHORE_SERVICE_BOUNDARY = MapBounds(north=31.75, south=31.25, east=74.65, west=74.05)
RADIUS_OPTIONS = [1000, 2000, 3000, 5000, 10000, 15000]
PROJECT_TYPES = [
    ProjectTypeOption(value="apartments", label="Apartments"),
    ProjectTypeOption(value="residential_tower", label="Residential towers"),
    ProjectTypeOption(value="commercial", label="Commercial projects"),
    ProjectTypeOption(value="mixed_use", label="Mixed-use projects"),
    ProjectTypeOption(value="shopping_mall", label="Shopping malls"),
    ProjectTypeOption(value="business_center", label="Business centers"),
    ProjectTypeOption(value="housing_society", label="Housing societies"),
    ProjectTypeOption(value="villas", label="Villas"),
    ProjectTypeOption(value="plot_development", label="Plot developments"),
    ProjectTypeOption(value="project_sales_office", label="Project sales offices"),
    ProjectTypeOption(value="other", label="Other developments"),
]
DEFAULT_PROJECT_TYPES = {"apartments", "commercial", "mixed_use", "residential_tower", "housing_society"}

LAHORE_ZONES = [
    LahoreZone(id="all_lahore", name="All Lahore", center=LAHORE_CENTER, zoom=11, bounds=LAHORE_SERVICE_BOUNDARY),
    LahoreZone(id="gulberg", name="Gulberg", center=MapPoint(lat=31.5106, lng=74.3441), zoom=14, bounds=MapBounds(north=31.535, south=31.485, east=74.375, west=74.315)),
    LahoreZone(id="dha_lahore", name="DHA Lahore", center=MapPoint(lat=31.4687, lng=74.4097), zoom=13, bounds=MapBounds(north=31.51, south=31.42, east=74.47, west=74.35)),
    LahoreZone(id="bahria_town", name="Bahria Town", center=MapPoint(lat=31.3703, lng=74.1846), zoom=13, bounds=MapBounds(north=31.405, south=31.33, east=74.235, west=74.145)),
    LahoreZone(id="johar_town", name="Johar Town", center=MapPoint(lat=31.4697, lng=74.2728), zoom=13, bounds=MapBounds(north=31.50, south=31.435, east=74.31, west=74.235)),
    LahoreZone(id="raiwind_road", name="Raiwind Road", center=MapPoint(lat=31.3839, lng=74.2462), zoom=12, bounds=MapBounds(north=31.47, south=31.30, east=74.33, west=74.17)),
    LahoreZone(id="lake_city", name="Lake City", center=MapPoint(lat=31.3535, lng=74.2555), zoom=14, bounds=MapBounds(north=31.38, south=31.33, east=74.285, west=74.225)),
    LahoreZone(id="model_town", name="Model Town", center=MapPoint(lat=31.4846, lng=74.3239), zoom=14, bounds=MapBounds(north=31.505, south=31.465, east=74.35, west=74.295)),
    LahoreZone(id="wapda_town", name="Wapda Town", center=MapPoint(lat=31.4337, lng=74.2651), zoom=14, bounds=MapBounds(north=31.46, south=31.41, east=74.295, west=74.235)),
    LahoreZone(id="canal_road", name="Canal Road", center=MapPoint(lat=31.4972, lng=74.2857), zoom=12, bounds=MapBounds(north=31.58, south=31.40, east=74.36, west=74.22)),
    LahoreZone(id="ferozepur_road", name="Ferozepur Road", center=MapPoint(lat=31.4668, lng=74.3352), zoom=12, bounds=MapBounds(north=31.55, south=31.38, east=74.38, west=74.29)),
    LahoreZone(id="jail_road", name="Jail Road", center=MapPoint(lat=31.5355, lng=74.3332), zoom=14, bounds=MapBounds(north=31.56, south=31.51, east=74.355, west=74.31)),
    LahoreZone(id="mall_road", name="Mall Road", center=MapPoint(lat=31.5657, lng=74.3142), zoom=14, bounds=MapBounds(north=31.585, south=31.545, east=74.35, west=74.285)),
    LahoreZone(id="cantt", name="Cantt", center=MapPoint(lat=31.5247, lng=74.3836), zoom=13, bounds=MapBounds(north=31.565, south=31.485, east=74.43, west=74.34)),
    LahoreZone(id="ring_road", name="Ring Road", center=MapPoint(lat=31.5482, lng=74.4542), zoom=11, bounds=MapBounds(north=31.70, south=31.35, east=74.62, west=74.25)),
    LahoreZone(id="bahria_orchard", name="Bahria Orchard", center=MapPoint(lat=31.3006, lng=74.2075), zoom=13, bounds=MapBounds(north=31.335, south=31.27, east=74.25, west=74.17)),
    LahoreZone(id="lda_avenue", name="LDA Avenue", center=MapPoint(lat=31.3942, lng=74.2397), zoom=14, bounds=MapBounds(north=31.42, south=31.37, east=74.27, west=74.21)),
    LahoreZone(id="new_lahore_city", name="New Lahore City", center=MapPoint(lat=31.3329, lng=74.1731), zoom=14, bounds=MapBounds(north=31.36, south=31.305, east=74.205, west=74.145)),
    LahoreZone(id="central_lahore", name="Central Lahore", center=MapPoint(lat=31.5497, lng=74.3436), zoom=12, bounds=MapBounds(north=31.61, south=31.49, east=74.40, west=74.28)),
]

def get_map_config() -> MapConfigRead:
    settings = get_settings()
    return MapConfigRead(
        city="Lahore",
        default_center=LAHORE_CENTER,
        default_zoom=11,
        service_boundary=LAHORE_SERVICE_BOUNDARY,
        radius_options=RADIUS_OPTIONS,
        project_types=PROJECT_TYPES,
        google_maps_configured=bool(settings.google_maps_browser_api_key),
    )


def get_lahore_zones() -> list[LahoreZone]:
    return LAHORE_ZONES


def get_zone(zone_id: str) -> LahoreZone | None:
    return next((zone for zone in LAHORE_ZONES if zone.id == zone_id), None)


def validate_project_search_config(config: ProjectSearchConfig) -> None:
    allowed_types = {item.value for item in PROJECT_TYPES}
    unknown_types = set(config.project_types) - allowed_types
    if unknown_types:
        raise InvalidOwnerError(f"Unknown project type: {sorted(unknown_types)[0]}.")

    if config.radius_meters is not None and (config.radius_meters < min(RADIUS_OPTIONS) or config.radius_meters > max(RADIUS_OPTIONS) or config.radius_meters % 1000 != 0):
        raise InvalidOwnerError("Radius must be a whole-kilometer value between 1 km and 15 km.")

    if config.search_mode == "zone":
        if config.zone_id is None or get_zone(config.zone_id) is None:
            raise InvalidOwnerError("Unknown Lahore zone.")

    points: list[MapPoint] = []
    if config.map_center is not None:
        points.append(config.map_center)
    if config.geometry is not None and config.geometry.type == "rectangle":
        assert config.geometry.north is not None
        assert config.geometry.south is not None
        assert config.geometry.east is not None
        assert config.geometry.west is not None
        points.extend(
            [
                MapPoint(lat=config.geometry.north, lng=config.geometry.east),
                MapPoint(lat=config.geometry.north, lng=config.geometry.west),
                MapPoint(lat=config.geometry.south, lng=config.geometry.east),
                MapPoint(lat=config.geometry.south, lng=config.geometry.west),
            ]
        )
    if config.geometry is not None and config.geometry.coordinates:
        points.extend(config.geometry.coordinates)

    for point in points:
        if not is_inside_lahore(point):
            raise InvalidOwnerError("The selected area falls outside the current Lahore service boundary.")


def is_inside_lahore(point: MapPoint) -> bool:
    return (
        LAHORE_SERVICE_BOUNDARY.south <= point.lat <= LAHORE_SERVICE_BOUNDARY.north
        and LAHORE_SERVICE_BOUNDARY.west <= point.lng <= LAHORE_SERVICE_BOUNDARY.east
    )

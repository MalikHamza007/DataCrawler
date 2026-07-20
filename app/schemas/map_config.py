from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class MapPoint(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class MapBounds(BaseModel):
    north: float = Field(ge=-90, le=90)
    south: float = Field(ge=-90, le=90)
    east: float = Field(ge=-180, le=180)
    west: float = Field(ge=-180, le=180)

    @model_validator(mode="after")
    def validate_bounds(self) -> "MapBounds":
        if self.north <= self.south:
            raise ValueError("north must be greater than south")
        if self.east <= self.west:
            raise ValueError("east must be greater than west")
        return self


class LahoreZone(BaseModel):
    id: str
    name: str
    center: MapPoint
    zoom: int = Field(ge=1, le=21)
    bounds: MapBounds | None = None


class ProjectTypeOption(BaseModel):
    value: str
    label: str


class MapConfigRead(BaseModel):
    city: str
    default_center: MapPoint
    default_zoom: int
    service_boundary: MapBounds
    radius_options: list[int]
    project_types: list[ProjectTypeOption]
    google_maps_configured: bool


class SearchGeometry(BaseModel):
    type: Literal["rectangle", "polygon"]
    north: float | None = Field(default=None, ge=-90, le=90)
    south: float | None = Field(default=None, ge=-90, le=90)
    east: float | None = Field(default=None, ge=-180, le=180)
    west: float | None = Field(default=None, ge=-180, le=180)
    coordinates: list[MapPoint] | None = None

    @model_validator(mode="after")
    def validate_geometry_shape(self) -> "SearchGeometry":
        if self.type == "rectangle":
            if None in (self.north, self.south, self.east, self.west):
                raise ValueError("rectangle geometry requires north, south, east, and west")
            if self.north <= self.south:
                raise ValueError("rectangle north must be greater than south")
            if self.east <= self.west:
                raise ValueError("rectangle east must be greater than west")
        if self.type == "polygon":
            if not self.coordinates or len(self.coordinates) < 3:
                raise ValueError("polygon geometry requires at least three points")
            if len(self.coordinates) > 100:
                raise ValueError("polygon geometry cannot contain more than 100 points")
            unique_points = {(point.lat, point.lng) for point in self.coordinates}
            if len(unique_points) < 3:
                raise ValueError("polygon geometry requires at least three unique points")
        return self


class ProjectSearchConfig(BaseModel):
    search_mode: Literal["zone", "radius", "rectangle", "polygon"]
    zone_id: str | None = None
    radius_meters: int | None = None
    project_types: list[str] = Field(min_length=1)
    map_center: MapPoint | None = None
    geometry: SearchGeometry | None = None

    @model_validator(mode="after")
    def validate_mode_requirements(self) -> "ProjectSearchConfig":
        if self.search_mode == "zone" and not self.zone_id:
            raise ValueError("zone mode requires zone_id")
        if self.search_mode == "radius" and (self.map_center is None or self.radius_meters is None):
            raise ValueError("radius mode requires map_center and radius_meters")
        if self.search_mode == "rectangle" and (self.geometry is None or self.geometry.type != "rectangle"):
            raise ValueError("rectangle mode requires rectangle geometry")
        if self.search_mode == "polygon" and (self.geometry is None or self.geometry.type != "polygon"):
            raise ValueError("polygon mode requires polygon geometry")
        return self

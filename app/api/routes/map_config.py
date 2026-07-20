from __future__ import annotations

from fastapi import APIRouter

from app.schemas.map_config import MapConfigRead
from app.services.lahore_zones import get_lahore_zones, get_map_config

router = APIRouter(tags=["Map Configuration"])


@router.get("/map-config", response_model=MapConfigRead)
def map_config() -> MapConfigRead:
    return get_map_config()


@router.get("/lahore-zones")
def lahore_zones() -> dict[str, object]:
    return {"items": get_lahore_zones()}

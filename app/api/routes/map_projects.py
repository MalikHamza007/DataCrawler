from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from app.api.dependencies import DbSession
from app.services.dashboard import map_projects

router = APIRouter(prefix="/map", tags=["Dashboard Map"])


@router.get("/projects")
def get_map_projects(
    db: DbSession,
    north: float,
    south: float,
    east: float,
    west: float,
    zoom: int = Query(default=12, ge=1, le=22),
    limit: int = Query(default=1000, ge=1, le=2000),
    lahore_zone: str | None = None,
    project_type: str | None = None,
    review_status: str | None = None,
    outreach_status: str | None = None,
) -> dict[str, Any]:
    return map_projects(db, north=north, south=south, east=east, west=west, limit=limit, filters={"lahore_zone": lahore_zone, "project_type": project_type, "review_status": review_status, "outreach_status": outreach_status})


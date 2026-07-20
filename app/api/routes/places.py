from __future__ import annotations

from fastapi import APIRouter, status

from app.api.dependencies import DbSession
from app.core.config import get_settings
from app.collectors.google_places.exceptions import GooglePlacesError
from app.core.exceptions import DomainError, PermissionDeniedError
from app.schemas.places import PlacesDiscoveryResult, PlacesStatusRead, SearchPlanRead
from app.services.places_discovery import discover_places_for_job, places_status, preview_places_plan

router = APIRouter(tags=["Google Places"])


@router.get("/places/status", response_model=PlacesStatusRead)
def get_places_status() -> dict[str, bool]:
    return places_status()


@router.post("/collection-jobs/{job_id}/places-plan", response_model=SearchPlanRead)
def get_places_plan(job_id: int, db: DbSession) -> SearchPlanRead:
    return preview_places_plan(db, job_id)


@router.post("/collection-jobs/{job_id}/run-discovery", response_model=PlacesDiscoveryResult, status_code=status.HTTP_200_OK)
def run_discovery(job_id: int, db: DbSession) -> PlacesDiscoveryResult:
    if get_settings().app_env != "development":
        raise PermissionDeniedError("Development discovery execution is only available in development.")
    try:
        return discover_places_for_job(db, job_id)
    except GooglePlacesError as exc:
        raise DomainError(str(exc)) from exc

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies import DbSession, pagination
from app.schemas.collection_job import CollectionJobCreate, CollectionJobRead, CollectionJobUpdate, CollectionLogCreate, CollectionLogRead
from app.services import collection_jobs as service
from app.services.research_summary import get_research_summary

router = APIRouter(prefix="/collection-jobs", tags=["Collection Jobs"])


@router.post("", response_model=CollectionJobRead, status_code=status.HTTP_201_CREATED)
def create_collection_job(payload: CollectionJobCreate, db: DbSession) -> object:
    return service.create_collection_job(db, payload)


@router.get("", response_model=list[CollectionJobRead])
def list_collection_jobs(
    db: DbSession,
    page: Annotated[tuple[int, int], Depends(pagination)],
    status: str | None = Query(default=None),
    job_type: str | None = Query(default=None),
    lahore_zone: str | None = Query(default=None),
) -> list[object]:
    offset, limit = page
    return service.list_collection_jobs(db, offset=offset, limit=limit, status=status, job_type=job_type, lahore_zone=lahore_zone)


@router.get("/{job_id}", response_model=CollectionJobRead)
def get_collection_job(job_id: int, db: DbSession) -> object:
    return service.get_collection_job(db, job_id)


@router.get("/{job_id}/research-summary")
def research_summary(job_id: int, db: DbSession) -> dict[str, object]:
    return get_research_summary(db, job_id)


@router.get("/{job_id}/logs", response_model=list[CollectionLogRead])
def get_collection_job_logs(
    job_id: int,
    db: DbSession,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    level: str | None = Query(default=None),
) -> list[object]:
    return service.list_collection_logs(db, job_id, offset=offset, limit=limit, level=level)


@router.patch("/{job_id}", response_model=CollectionJobRead)
def update_collection_job(job_id: int, payload: CollectionJobUpdate, db: DbSession) -> object:
    return service.update_collection_job(db, job_id, payload)


@router.post("/{job_id}/logs", response_model=CollectionLogRead, status_code=status.HTTP_201_CREATED)
def add_collection_log(job_id: int, payload: CollectionLogCreate, db: DbSession) -> object:
    return service.add_collection_log(db, job_id, payload)


@router.post("/{job_id}/cancel", response_model=CollectionJobRead)
def cancel_collection_job(job_id: int, db: DbSession) -> object:
    job = service.cancel_collection_job(db, job_id)
    return job


@router.post("/{job_id}/retry", response_model=CollectionJobRead)
def retry_collection_job(job_id: int, db: DbSession) -> object:
    return service.retry_collection_job(db, job_id)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_collection_job(job_id: int, db: DbSession) -> Response:
    service.delete_collection_job(db, job_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

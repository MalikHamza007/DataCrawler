from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.encoders import jsonable_encoder

from app.api.dependencies import DbSession, pagination
from app.schemas.common import DeveloperLink
from app.schemas.project import ProjectCreate, ProjectMutationResponse, ProjectRead, ProjectReviewRequest, ProjectUpdate
from app.services import dashboard as dashboard_service
from app.services import projects as service

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: DbSession) -> object:
    return service.create_project(db, payload)


@router.get("", response_model=list[ProjectRead])
def list_projects(
    db: DbSession,
    page: Annotated[tuple[int, int], Depends(pagination)],
    developer_id: int | None = Query(default=None),
    lahore_zone: str | None = Query(default=None),
    project_type: str | None = Query(default=None),
    project_status: str | None = Query(default=None),
    verification_status: str | None = Query(default=None),
    name: str | None = Query(default=None),
    include_merged: bool = Query(default=False),
) -> list[object]:
    offset, limit = page
    return service.list_projects(
        db,
        offset=offset,
        limit=limit,
        developer_id=developer_id,
        lahore_zone=lahore_zone,
        project_type=project_type,
        project_status=project_status,
        verification_status=verification_status,
        name=name,
        include_merged=include_merged,
    )


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: int, db: DbSession) -> object:
    return service.get_project(db, project_id)


@router.patch("/{project_id}", response_model=None)
def update_project(project_id: int, payload: ProjectUpdate, db: DbSession) -> object:
    if payload.expected_version is not None:
        return service.update_project_with_response(db, project_id, payload)
    return service.update_project(db, project_id, payload)


@router.post("/{project_id}/review", response_model=ProjectMutationResponse)
def review_project(project_id: int, payload: ProjectReviewRequest, db: DbSession) -> object:
    return service.review_project(db, project_id, payload)


@router.get("/{project_id}/dashboard-detail")
def project_dashboard_detail(project_id: int, db: DbSession) -> dict:
    return jsonable_encoder(dashboard_service.project_detail(db, project_id))


@router.patch("/{project_id}/developer", response_model=ProjectRead)
def set_project_developer(project_id: int, payload: DeveloperLink, db: DbSession) -> object:
    return service.set_project_developer(db, project_id, payload)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, db: DbSession) -> Response:
    service.delete_project(db, project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.encoders import jsonable_encoder

from app.api.dependencies import DbSession, pagination
from app.schemas.developer import DeveloperCreate, DeveloperMutationResponse, DeveloperRead, DeveloperReviewRequest, DeveloperUpdate, DeveloperWithProjects
from app.services import dashboard as dashboard_service
from app.services import developers as service

router = APIRouter(prefix="/developers", tags=["Developers"])


@router.post("", response_model=DeveloperRead, status_code=status.HTTP_201_CREATED)
def create_developer(payload: DeveloperCreate, db: DbSession) -> object:
    return service.create_developer(db, payload)


@router.get("", response_model=list[DeveloperRead])
def list_developers(
    db: DbSession,
    page: Annotated[tuple[int, int], Depends(pagination)],
    name: str | None = Query(default=None),
    classification: str | None = Query(default=None),
    verification_status: str | None = Query(default=None),
    include_merged: bool = Query(default=False),
) -> list[object]:
    offset, limit = page
    return service.list_developers(
        db,
        offset=offset,
        limit=limit,
        name=name,
        classification=classification,
        verification_status=verification_status,
        include_merged=include_merged,
    )


@router.get("/{developer_id}", response_model=DeveloperWithProjects)
def get_developer(developer_id: int, db: DbSession) -> object:
    return service.get_developer(db, developer_id)


@router.patch("/{developer_id}", response_model=None)
def update_developer(developer_id: int, payload: DeveloperUpdate, db: DbSession) -> object:
    if payload.expected_version is not None:
        return service.update_developer_with_response(db, developer_id, payload)
    return service.update_developer(db, developer_id, payload)


@router.post("/{developer_id}/review", response_model=DeveloperMutationResponse)
def review_developer(developer_id: int, payload: DeveloperReviewRequest, db: DbSession) -> object:
    return service.review_developer(db, developer_id, payload)


@router.get("/{developer_id}/dashboard-detail")
def developer_dashboard_detail(developer_id: int, db: DbSession) -> dict:
    return jsonable_encoder(dashboard_service.developer_detail(db, developer_id))


@router.delete("/{developer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_developer(developer_id: int, db: DbSession) -> Response:
    service.delete_developer(db, developer_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

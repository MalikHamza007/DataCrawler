from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies import DbSession, pagination
from app.schemas.social_profile import SocialProfileCreate, SocialProfileRead, SocialProfileUpdate
from app.services import social_profiles as service

router = APIRouter(prefix="/social-profiles", tags=["Social Profiles"])


@router.post("", response_model=SocialProfileRead, status_code=status.HTTP_201_CREATED)
def create_social_profile(payload: SocialProfileCreate, db: DbSession) -> object:
    return service.create_social_profile(db, payload)


@router.get("", response_model=list[SocialProfileRead])
def list_social_profiles(
    db: DbSession,
    page: Annotated[tuple[int, int], Depends(pagination)],
    developer_id: int | None = Query(default=None),
    project_id: int | None = Query(default=None),
    platform: str | None = Query(default=None),
    is_official: bool | None = Query(default=None),
) -> list[object]:
    offset, limit = page
    return service.list_social_profiles(
        db,
        offset=offset,
        limit=limit,
        developer_id=developer_id,
        project_id=project_id,
        platform=platform,
        is_official=is_official,
    )


@router.get("/{profile_id}", response_model=SocialProfileRead)
def get_social_profile(profile_id: int, db: DbSession) -> object:
    return service.get_social_profile(db, profile_id)


@router.patch("/{profile_id}", response_model=SocialProfileRead)
def update_social_profile(profile_id: int, payload: SocialProfileUpdate, db: DbSession) -> object:
    return service.update_social_profile(db, profile_id, payload)


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_social_profile(profile_id: int, db: DbSession) -> Response:
    service.delete_social_profile(db, profile_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

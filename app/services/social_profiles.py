from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import EntityNotFoundError
from app.models.social_profile import SocialProfile
from app.repositories.social_profiles import social_profile_repository
from app.schemas.social_profile import SocialProfileCreate, SocialProfileUpdate
from app.services.developers import get_developer
from app.services.normalization import normalize_url
from app.services.projects import get_project


def get_social_profile(db: Session, profile_id: int) -> SocialProfile:
    profile = social_profile_repository.get(db, profile_id)
    if profile is None:
        raise EntityNotFoundError(f"Social profile {profile_id} was not found.")
    return profile


def _validate_owner(db: Session, developer_id: int | None, project_id: int | None) -> None:
    if developer_id is not None:
        get_developer(db, developer_id)
    if project_id is not None:
        get_project(db, project_id)


def list_social_profiles(
    db: Session,
    *,
    offset: int,
    limit: int,
    developer_id: int | None = None,
    project_id: int | None = None,
    platform: str | None = None,
    is_official: bool | None = None,
) -> list[SocialProfile]:
    return social_profile_repository.list(
        db,
        offset=offset,
        limit=limit,
        filters={
            "developer_id": developer_id,
            "project_id": project_id,
            "platform": platform,
            "is_official": is_official,
        },
    )


def create_social_profile(db: Session, payload: SocialProfileCreate) -> SocialProfile:
    _validate_owner(db, payload.developer_id, payload.project_id)
    data = payload.model_dump()
    data["normalized_url"] = normalize_url(payload.profile_url)
    return social_profile_repository.create(db, data)


def update_social_profile(db: Session, profile_id: int, payload: SocialProfileUpdate) -> SocialProfile:
    profile = get_social_profile(db, profile_id)
    data = payload.model_dump(exclude_unset=True)
    if "profile_url" in data:
        data["normalized_url"] = normalize_url(data["profile_url"])
    return social_profile_repository.update(db, profile, data)


def delete_social_profile(db: Session, profile_id: int) -> None:
    social_profile_repository.delete(db, get_social_profile(db, profile_id))

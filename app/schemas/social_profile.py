from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from app.schemas.common import ORMModel, UrlStr

Platform = Literal["facebook", "instagram", "x", "linkedin", "youtube", "tiktok", "other"]


class SocialProfileBase(ORMModel):
    developer_id: int | None = None
    project_id: int | None = None
    platform: Platform
    profile_name: str | None = Field(default=None, max_length=255)
    profile_url: UrlStr
    is_official: bool = False
    verification_status: str = Field(default="unverified", max_length=50)

    @model_validator(mode="after")
    def validate_owner(self) -> "SocialProfileBase":
        if (self.developer_id is None) == (self.project_id is None):
            raise ValueError("exactly one of developer_id or project_id is required")
        return self


class SocialProfileCreate(SocialProfileBase):
    pass


class SocialProfileUpdate(ORMModel):
    platform: Platform | None = None
    profile_name: str | None = Field(default=None, max_length=255)
    profile_url: UrlStr | None = None
    is_official: bool | None = None
    verification_status: str | None = Field(default=None, max_length=50)


class SocialProfileRead(SocialProfileBase):
    id: int
    normalized_url: str | None
    created_at: datetime
    updated_at: datetime

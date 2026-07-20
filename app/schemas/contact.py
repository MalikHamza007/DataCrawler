from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from app.schemas.common import ORMModel, UrlStr

ContactType = Literal["phone", "mobile", "whatsapp", "landline", "email", "address", "other"]


class ContactBase(ORMModel):
    developer_id: int | None = None
    project_id: int | None = None
    contact_type: ContactType
    label: str | None = Field(default=None, max_length=255)
    value: str = Field(min_length=1, max_length=2048)
    person_name: str | None = Field(default=None, max_length=255)
    designation: str | None = Field(default=None, max_length=255)
    is_primary: bool = False
    is_public_business_contact: bool = True
    verification_status: str = Field(default="unverified", max_length=50)
    source_url: UrlStr | None = None

    @model_validator(mode="after")
    def validate_owner(self) -> "ContactBase":
        if (self.developer_id is None) == (self.project_id is None):
            raise ValueError("exactly one of developer_id or project_id is required")
        return self


class ContactCreate(ContactBase):
    pass


class ContactUpdate(ORMModel):
    contact_type: ContactType | None = None
    label: str | None = Field(default=None, max_length=255)
    value: str | None = Field(default=None, min_length=1, max_length=2048)
    person_name: str | None = Field(default=None, max_length=255)
    designation: str | None = Field(default=None, max_length=255)
    is_primary: bool | None = None
    is_public_business_contact: bool | None = None
    verification_status: str | None = Field(default=None, max_length=50)
    source_url: UrlStr | None = None


class ContactRead(ContactBase):
    id: int
    normalized_value: str | None
    created_at: datetime
    updated_at: datetime

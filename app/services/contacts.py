from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import EntityNotFoundError
from app.models.contact import Contact
from app.repositories.contacts import contact_repository
from app.schemas.contact import ContactCreate, ContactUpdate
from app.services.developers import get_developer
from app.services.normalization import normalize_contact_value
from app.services.projects import get_project


def get_contact(db: Session, contact_id: int) -> Contact:
    contact = contact_repository.get(db, contact_id)
    if contact is None:
        raise EntityNotFoundError(f"Contact {contact_id} was not found.")
    return contact


def _validate_owner(db: Session, developer_id: int | None, project_id: int | None) -> None:
    if developer_id is not None:
        get_developer(db, developer_id)
    if project_id is not None:
        get_project(db, project_id)


def list_contacts(
    db: Session,
    *,
    offset: int,
    limit: int,
    developer_id: int | None = None,
    project_id: int | None = None,
    contact_type: str | None = None,
    verification_status: str | None = None,
) -> list[Contact]:
    return contact_repository.list(
        db,
        offset=offset,
        limit=limit,
        filters={
            "developer_id": developer_id,
            "project_id": project_id,
            "contact_type": contact_type,
            "verification_status": verification_status,
        },
    )


def create_contact(db: Session, payload: ContactCreate) -> Contact:
    _validate_owner(db, payload.developer_id, payload.project_id)
    data = payload.model_dump()
    data["normalized_value"] = normalize_contact_value(payload.value, payload.contact_type)
    return contact_repository.create(db, data)


def update_contact(db: Session, contact_id: int, payload: ContactUpdate) -> Contact:
    contact = get_contact(db, contact_id)
    data = payload.model_dump(exclude_unset=True)
    contact_type = data.get("contact_type", contact.contact_type)
    value = data.get("value", contact.value)
    if "contact_type" in data or "value" in data:
        data["normalized_value"] = normalize_contact_value(value, contact_type)
    return contact_repository.update(db, contact, data)


def delete_contact(db: Session, contact_id: int) -> None:
    contact_repository.delete(db, get_contact(db, contact_id))

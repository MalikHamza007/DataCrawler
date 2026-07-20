from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies import DbSession, pagination
from app.schemas.contact import ContactCreate, ContactRead, ContactUpdate
from app.services import contacts as service

router = APIRouter(prefix="/contacts", tags=["Contacts"])


@router.post("", response_model=ContactRead, status_code=status.HTTP_201_CREATED)
def create_contact(payload: ContactCreate, db: DbSession) -> object:
    return service.create_contact(db, payload)


@router.get("", response_model=list[ContactRead])
def list_contacts(
    db: DbSession,
    page: Annotated[tuple[int, int], Depends(pagination)],
    developer_id: int | None = Query(default=None),
    project_id: int | None = Query(default=None),
    contact_type: str | None = Query(default=None),
    verification_status: str | None = Query(default=None),
) -> list[object]:
    offset, limit = page
    return service.list_contacts(
        db,
        offset=offset,
        limit=limit,
        developer_id=developer_id,
        project_id=project_id,
        contact_type=contact_type,
        verification_status=verification_status,
    )


@router.get("/{contact_id}", response_model=ContactRead)
def get_contact(contact_id: int, db: DbSession) -> object:
    return service.get_contact(db, contact_id)


@router.patch("/{contact_id}", response_model=ContactRead)
def update_contact(contact_id: int, payload: ContactUpdate, db: DbSession) -> object:
    return service.update_contact(db, contact_id, payload)


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contact(contact_id: int, db: DbSession) -> Response:
    service.delete_contact(db, contact_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

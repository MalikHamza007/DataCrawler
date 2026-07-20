from __future__ import annotations

from fastapi import APIRouter, Header, Query, Request

from app.api.dependencies import DbSession
from app.core.config import get_settings
from app.schemas.social_capture import EntitySearchResponse
from app.services.entity_search import search_entities
from app.services.extension_auth import validate_extension_request

router = APIRouter(prefix="/entities", tags=["Entity Search"])


@router.get("/search", response_model=EntitySearchResponse)
def search(
    request: Request,
    db: DbSession,
    q: str = Query(default="", max_length=255),
    entity_type: str = Query(default="all", pattern="^(developer|project|all)$"),
    limit: int = Query(default=10, ge=1, le=25),
    include_merged: bool = Query(default=False),
    x_alduor_extension_token: str | None = Header(default=None),
    origin: str | None = Header(default=None),
) -> EntitySearchResponse:
    content_length = request.headers.get("content-length")
    validate_extension_request(
        settings=get_settings(),
        token=x_alduor_extension_token,
        origin=origin,
        content_length=int(content_length) if content_length and content_length.isdigit() else None,
    )
    return search_entities(db, q=q, entity_type=entity_type, limit=limit, include_merged=include_merged)


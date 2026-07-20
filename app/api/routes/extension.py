from __future__ import annotations

from fastapi import APIRouter, Header, Request

from app.core.config import get_settings
from app.schemas.extension import ExtensionStatus
from app.services.extension_auth import validate_extension_request

router = APIRouter(prefix="/extension", tags=["Extension"])


@router.get("/status", response_model=ExtensionStatus)
def extension_status(
    request: Request,
    x_alduor_extension_token: str | None = Header(default=None),
    origin: str | None = Header(default=None),
) -> ExtensionStatus:
    settings = get_settings()
    content_length = request.headers.get("content-length")
    validate_extension_request(
        settings=settings,
        token=x_alduor_extension_token,
        origin=origin,
        content_length=int(content_length) if content_length and content_length.isdigit() else None,
    )
    return ExtensionStatus(enabled=settings.alduor_extension_enabled, connected=True, app_name=settings.app_name)


from __future__ import annotations

import hmac

from app.core.config import Settings
from app.core.exceptions import PermissionDeniedError


def validate_extension_request(
    *,
    settings: Settings,
    token: str | None,
    origin: str | None = None,
    content_length: int | None = None,
) -> None:
    if not settings.alduor_extension_enabled:
        raise PermissionDeniedError("Extension integration is disabled.")
    if content_length is not None and content_length > settings.alduor_extension_max_capture_bytes:
        raise PermissionDeniedError("Capture payload was too large.")
    if settings.alduor_extension_allowed_origins and origin not in settings.alduor_extension_allowed_origins:
        raise PermissionDeniedError("Extension origin is not allowed.")
    configured = settings.alduor_extension_api_token
    if not configured:
        if settings.app_env == "development":
            configured = "local-token"
        else:
            raise PermissionDeniedError("Extension token is not configured.")
    if not token or not hmac.compare_digest(token, configured):
        raise PermissionDeniedError("Invalid extension token.")


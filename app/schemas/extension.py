from __future__ import annotations

from app.schemas.common import ORMModel


class ExtensionStatus(ORMModel):
    enabled: bool
    connected: bool
    app_name: str
    supported_capture_version: str = "1"
    extension_version_minimum: str = "0.1.0"


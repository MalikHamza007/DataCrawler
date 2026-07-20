from __future__ import annotations

import os
from pathlib import Path

APP_VERSION = "0.10.0"
EXPORT_SCHEMA_VERSION = "m9-v1"
EXTENSION_PROTOCOL_VERSION = "1"


def version_info() -> dict[str, str | None]:
    root = Path(__file__).resolve().parents[3]
    version_file = root / "VERSION"
    version = version_file.read_text(encoding="utf-8").strip() if version_file.exists() else APP_VERSION
    return {
        "application_version": version,
        "git_commit": os.getenv("GIT_COMMIT"),
        "build_time": os.getenv("BUILD_TIME"),
    }

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text

from app.core.config import Settings, get_settings
from app.core.version import version_info
from app.db.session import SessionLocal

BACKUP_VERSION = "m10-v1"


def utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def database_path(settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    if not settings.database_url.startswith("sqlite:///"):
        raise ValueError("Only SQLite databases are supported.")
    raw = settings.database_url.removeprefix("sqlite:///")
    return Path(raw if raw.startswith("/") else Path.cwd() / raw).resolve()


def safe_root(value: str) -> Path:
    path = Path(value)
    resolved = (Path.cwd() / path).resolve() if not path.is_absolute() else path.resolve()
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def sanitize_label(value: str | None) -> str:
    text_value = (value or "").strip().lower()
    text_value = re.sub(r"[^a-z0-9_-]+", "_", text_value)
    text_value = re.sub(r"_+", "_", text_value).strip("_")
    return text_value[:60]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def quick_check(path: Path | None = None, *, full: bool = False) -> str:
    target = path or database_path()
    pragma = "integrity_check" if full else "quick_check"
    with sqlite3.connect(f"file:{target}?mode=ro", uri=True) as connection:
        return str(connection.execute(f"PRAGMA {pragma}").fetchone()[0])


def alembic_head() -> str:
    config = Config("alembic.ini")
    script = ScriptDirectory.from_config(config)
    return str(script.get_current_head())


def alembic_current() -> str | None:
    with SessionLocal() as db:
        result = db.execute(text("SELECT version_num FROM alembic_version")).first()
        return str(result[0]) if result else None


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def backup_manifest(directory: Path) -> dict[str, Any]:
    return json.loads((directory / "manifest.json").read_text(encoding="utf-8"))


def assert_inside(root: Path, path: Path) -> Path:
    resolved = path.resolve()
    if root.resolve() not in resolved.parents and root.resolve() != resolved:
        raise ValueError("Path escapes approved root.")
    return resolved


def app_version() -> str:
    return str(version_info()["application_version"])

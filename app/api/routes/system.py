from __future__ import annotations

from pathlib import Path
import shutil

from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.version import EXPORT_SCHEMA_VERSION, EXTENSION_PROTOCOL_VERSION, version_info
from app.db.session import get_db
from app.models import ExportArtifact
from app.services.worker_leases import get_worker_status

router = APIRouter(prefix="/system", tags=["System"])


@router.get("/status")
def system_status(db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> dict:
    db.execute(text("SELECT 1"))
    integrity = db.execute(text("PRAGMA quick_check")).scalar()
    worker = get_worker_status(db, settings)
    info = version_info()
    return {
        "status": "ready" if integrity == "ok" else "degraded",
        "application": settings.app_name,
        "version": info["application_version"],
        "environment": settings.app_env,
        "database": {"reachable": True, "schema_current": _schema_current(), "integrity": integrity},
        "worker": {"status": worker["status"], "heartbeat_at": worker.get("heartbeat_at")},
        "storage": {"exports_writable": _writable(settings.export_directory), "backups_writable": _writable(settings.backup_directory)},
        "features": {
            "google_maps_configured": bool(settings.google_maps_browser_api_key and settings.google_maps_map_id),
            "google_places_enabled": settings.google_places_enabled,
            "website_crawler_enabled": settings.website_crawler_enabled,
            "extension_enabled": settings.alduor_extension_enabled,
            "exports_enabled": settings.export_enabled,
        },
        "metadata": {
            "export_schema_version": EXPORT_SCHEMA_VERSION,
            "intelligence_rule_version": settings.intelligence_rule_version,
            "extension_protocol_version": EXTENSION_PROTOCOL_VERSION,
            "git_commit": info["git_commit"],
            "build_time": info["build_time"],
        },
    }


@router.get("/storage")
def storage_status(db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> dict:
    expired_exports = db.query(ExportArtifact).filter(ExportArtifact.status == "ready", ExportArtifact.expires_at.is_not(None)).count()
    return {
        "database_size_bytes": _size_from_database_url(settings.database_url),
        "exports_size_bytes": _directory_size(settings.export_directory),
        "backups_size_bytes": _directory_size(settings.backup_directory),
        "logs_size_bytes": _directory_size(settings.log_directory),
        "free_disk_bytes": shutil.disk_usage(Path.cwd()).free,
        "expired_exports": expired_exports,
        "backup_count": len([path for path in _safe_path(settings.backup_directory).glob("alduor_backup_*") if path.is_dir()]),
    }


def _schema_current() -> bool:
    try:
        config = Config("alembic.ini")
        script = ScriptDirectory.from_config(config)
        return bool(script.get_current_head())
    except Exception:
        return False


def _safe_path(value: str) -> Path:
    path = Path(value)
    return (Path.cwd() / path).resolve() if not path.is_absolute() else path.resolve()


def _writable(value: str) -> bool:
    try:
        path = _safe_path(value)
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def _directory_size(value: str) -> int:
    path = _safe_path(value)
    if not path.exists():
        return 0
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def _size_from_database_url(database_url: str) -> int:
    if not database_url.startswith("sqlite:///"):
        return 0
    raw = database_url.removeprefix("sqlite:///")
    path = Path(raw if raw.startswith("/") else Path.cwd() / raw)
    return path.stat().st_size if path.exists() else 0

from __future__ import annotations

from pathlib import Path

from app.core.config import Settings


class StartupValidationError(RuntimeError):
    pass


def validate_startup(settings: Settings) -> None:
    errors: list[str] = []
    if not settings.database_url:
        errors.append("DATABASE_URL is required.")
    if not settings.database_url.startswith("sqlite:///"):
        errors.append("Only SQLite DATABASE_URL values are supported for the local MVP.")
    for label, path_value in (
        ("export", settings.export_directory),
        ("backup", settings.backup_directory),
        ("log", settings.log_directory),
    ):
        path = Path(path_value)
        if not path.is_absolute():
            path = Path.cwd() / path
        try:
            path.mkdir(parents=True, exist_ok=True)
            probe = path / ".write-test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
        except OSError:
            errors.append(f"{label.title()} directory is not writable.")
    db_path = _sqlite_path(settings.database_url)
    if db_path:
        try:
            db_path.parent.mkdir(parents=True, exist_ok=True)
            probe = db_path.parent / ".write-test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
        except OSError:
            errors.append("Database directory is not writable.")
    if settings.app_env == "release":
        if settings.docs_enabled:
            errors.append("DOCS_ENABLED must be false in release mode.")
        if "*" in settings.allowed_hosts:
            errors.append("Wildcard ALLOWED_HOSTS is not allowed in release mode.")
    if errors:
        raise StartupValidationError("Startup validation failed: " + " ".join(errors))


def _sqlite_path(database_url: str) -> Path | None:
    if not database_url.startswith("sqlite:///"):
        return None
    raw = database_url.removeprefix("sqlite:///")
    return Path(raw if raw.startswith("/") else Path.cwd() / raw)

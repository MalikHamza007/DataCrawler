from __future__ import annotations

import importlib.util
import shutil
import sys

from app.commands._ops import alembic_current, alembic_head, quick_check, safe_root
from app.core.config import get_settings
from app.core.startup_validation import validate_startup
from app.db.session import SessionLocal
from app.services.worker_leases import get_worker_status


def main() -> int:
    settings = get_settings()
    failures = 0
    warnings = 0

    def line(state: str, message: str) -> None:
        print(f"[{state}] {message}")

    try:
        validate_startup(settings)
        line("PASS", "Configuration validation passed")
    except Exception as exc:
        failures += 1
        line("FAIL", str(exc))
    line("PASS" if sys.version_info[:2] == (3, 12) else "WARN", f"Python {sys.version.split()[0]} detected")
    try:
        current, head = alembic_current(), alembic_head()
        if current == head:
            line("PASS", "Alembic schema current")
        else:
            failures += 1
            line("FAIL", f"Schema {current} != {head}")
        line("PASS" if quick_check() == "ok" else "FAIL", "Database quick_check")
    except Exception as exc:
        failures += 1
        line("FAIL", f"Database check failed: {exc}")
    for label, path in (("Export directory", settings.export_directory), ("Backup directory", settings.backup_directory), ("Log directory", settings.log_directory)):
        try:
            safe_root(path)
            line("PASS", f"{label} writable")
        except Exception:
            failures += 1
            line("FAIL", f"{label} not writable")
    with SessionLocal() as db:
        worker = get_worker_status(db, settings)
    if worker["status"] == "online":
        line("PASS", "Worker online")
    else:
        warnings += 1
        line("WARN", "Worker offline")
    line("PASS" if settings.google_maps_browser_api_key and settings.google_maps_map_id else "WARN", "Google Maps configuration")
    line("PASS" if settings.google_places_enabled else "WARN", "Google Places disabled")
    line("PASS" if settings.alduor_extension_api_token else "WARN", "Extension token configured")
    line("PASS" if importlib.util.find_spec("openpyxl") else "FAIL", "openpyxl available")
    line("PASS" if shutil.disk_usage(safe_root(settings.export_directory)).free >= settings.min_free_disk_bytes else "FAIL", "Disk free space")
    if failures:
        return 1
    return 2 if warnings else 0


if __name__ == "__main__":
    raise SystemExit(main())

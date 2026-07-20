from __future__ import annotations

import argparse
import sqlite3

from app.commands._ops import BACKUP_VERSION, alembic_current, app_version, database_path, quick_check, safe_root, sanitize_label, sha256, utc_stamp, write_json
from app.core.config import get_settings


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a consistent SQLite backup.")
    parser.add_argument("--label", default="", help="Optional safe backup label.")
    parser.add_argument("--output-dir", default=None, help="Approved backup root override.")
    parser.add_argument("--verify-only", action="store_true", help="Only verify the live database.")
    args = parser.parse_args()
    source = database_path()
    if args.verify_only:
        print(f"Live database quick_check: {quick_check(source)}")
        return 0
    settings = get_settings()
    root = safe_root(args.output_dir or settings.backup_directory)
    label = sanitize_label(args.label)
    name = f"alduor_backup_{utc_stamp()}" + (f"_{label}" if label else "")
    target_dir = root / name
    temp_dir = root / f".{name}.part"
    temp_dir.mkdir(parents=True, exist_ok=False)
    destination = temp_dir / "database.sqlite3"
    with sqlite3.connect(source) as src, sqlite3.connect(destination) as dst:
        src.backup(dst)
    integrity = quick_check(destination)
    if integrity != "ok":
        raise SystemExit(f"Backup integrity check failed: {integrity}")
    digest = sha256(destination)
    manifest = {
        "backup_version": BACKUP_VERSION,
        "application_version": app_version(),
        "schema_revision": alembic_current(),
        "created_at": utc_stamp(),
        "database_filename": "database.sqlite3",
        "database_size_bytes": destination.stat().st_size,
        "database_sha256": digest,
        "integrity_check": "ok",
        "included_exports": False,
        "included_configuration": False,
    }
    write_json(temp_dir / "manifest.json", manifest)
    (temp_dir / "SHA256SUMS").write_text(f"{digest}  database.sqlite3\n", encoding="utf-8")
    temp_dir.rename(target_dir)
    print(f"Backup created: {target_dir.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

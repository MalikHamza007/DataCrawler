from __future__ import annotations

import argparse
from pathlib import Path

from app.commands._ops import BACKUP_VERSION, backup_manifest, quick_check, sha256


def verify(directory: Path) -> None:
    manifest = backup_manifest(directory)
    if manifest.get("backup_version") != BACKUP_VERSION:
        raise ValueError("Unsupported backup version.")
    database = directory / manifest["database_filename"]
    if not database.exists():
        raise ValueError("Backup database is missing.")
    if sha256(database) != manifest.get("database_sha256"):
        raise ValueError("Backup SHA-256 mismatch.")
    if quick_check(database) != "ok":
        raise ValueError("Backup integrity check failed.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify an Alduor database backup.")
    parser.add_argument("backup_directory")
    args = parser.parse_args()
    try:
        verify(Path(args.backup_directory))
    except Exception as exc:
        print(f"Backup verification failed: {exc}")
        return 1
    print("Backup verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import shutil
from datetime import UTC, datetime, timedelta

from app.core.config import get_settings
from app.commands._ops import safe_root


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean old database backups.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--keep-latest", type=int, default=1)
    args = parser.parse_args()
    settings = get_settings()
    root = safe_root(settings.backup_directory)
    backups = sorted([path for path in root.glob("alduor_backup_*") if path.is_dir()], key=lambda path: path.stat().st_mtime, reverse=True)
    cutoff = datetime.now(UTC).timestamp() - timedelta(days=settings.backup_retention_days).total_seconds()
    delete = [path for index, path in enumerate(backups) if index >= max(1, args.keep_latest) and (index >= settings.backup_max_count or path.stat().st_mtime < cutoff)]
    for path in delete:
        print(("Would delete " if args.dry_run else "Deleting ") + path.name)
        if not args.dry_run:
            shutil.rmtree(path)
    print(f"Backups retained: {len(backups) - len(delete)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

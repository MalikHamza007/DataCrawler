from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

from app.commands._ops import database_path, quick_check, utc_stamp
from app.commands.backup_database import main as backup_main
from app.commands.verify_backup import verify


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore the SQLite database from a verified backup.")
    parser.add_argument("backup_directory")
    parser.add_argument("--yes", action="store_true", help="Confirm restore without prompt.")
    args = parser.parse_args()
    backup_dir = Path(args.backup_directory).resolve()
    if not args.yes:
        response = input("Restore will replace the live database. Type RESTORE to continue: ")
        if response != "RESTORE":
            print("Restore cancelled.")
            return 1
    verify(backup_dir)
    live = database_path()
    safety_name = f"pre_restore_{utc_stamp()}"
    print(f"Creating pre-restore safety backup: {safety_name}")
    old_argv = os.sys.argv[:]
    try:
        os.sys.argv = ["backup_database", "--label", safety_name]
        backup_main()
    finally:
        os.sys.argv = old_argv
    source = backup_dir / "database.sqlite3"
    temp = live.with_suffix(".restore.tmp")
    shutil.copy2(source, temp)
    if quick_check(temp) != "ok":
        temp.unlink(missing_ok=True)
        print("Restore integrity check failed.")
        return 1
    temp.replace(live)
    print("Database restored. Run migrations before starting services if required.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

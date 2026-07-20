from __future__ import annotations

import argparse
import sqlite3

from app.commands._ops import database_path, quick_check


def main() -> int:
    parser = argparse.ArgumentParser(description="Run safe SQLite maintenance.")
    parser.add_argument("--checkpoint", action="store_true")
    parser.add_argument("--optimize", action="store_true")
    parser.add_argument("--quick-check", action="store_true")
    parser.add_argument("--vacuum", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    path = database_path()
    if args.quick_check or not any((args.checkpoint, args.optimize, args.vacuum)):
        print(f"quick_check: {quick_check(path)}")
    with sqlite3.connect(path) as connection:
        if args.optimize or not any((args.checkpoint, args.quick_check, args.vacuum)):
            connection.execute("PRAGMA optimize")
            print("optimize: ok")
        if args.checkpoint or not any((args.optimize, args.quick_check, args.vacuum)):
            print(f"wal_checkpoint: {connection.execute('PRAGMA wal_checkpoint(PASSIVE)').fetchall()}")
        if args.vacuum:
            if not args.force:
                print("VACUUM requires --force.")
                return 1
            connection.execute("VACUUM")
            print("vacuum: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

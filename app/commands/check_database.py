from __future__ import annotations

import argparse

from app.commands._ops import quick_check


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a SQLite database integrity check.")
    parser.add_argument("--full", action="store_true", help="Run PRAGMA integrity_check instead of quick_check.")
    args = parser.parse_args()
    result = quick_check(full=args.full)
    print(f"Database integrity check: {result}")
    return 0 if result == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())

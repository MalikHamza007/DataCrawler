from __future__ import annotations

import argparse
import json

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.exports import cleanup_expired_exports


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean expired Alduor export files.")
    parser.add_argument("--dry-run", action="store_true", help="Report what would be removed without changing files or metadata.")
    args = parser.parse_args()
    settings = get_settings()
    with SessionLocal() as db:
        result = cleanup_expired_exports(db, settings, dry_run=args.dry_run)
        if not args.dry_run:
            db.commit()
    print(json.dumps({"dry_run": args.dry_run, **result}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

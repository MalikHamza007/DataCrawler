from __future__ import annotations

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.worker_leases import get_worker_status


def main() -> int:
    settings = get_settings()
    with SessionLocal() as db:
        status = get_worker_status(db, settings)
    if status["status"] != "online":
        print("worker unhealthy: offline")
        return 1
    print("worker healthy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.db.base import utc_now
from app.db.session import get_db
from app.main import app
from app.services.worker_leases import WorkerLeaseActiveError, acquire_worker_lease, get_worker_status, release_worker_lease, renew_worker_lease


def db_from_app() -> object:
    generator = app.dependency_overrides[get_db]()
    return next(generator), generator


def test_worker_lease_acquire_renew_reject_reclaim_and_release(client: TestClient) -> None:
    db, generator = db_from_app()
    settings = Settings(worker_lease_seconds=60)
    try:
        lease = acquire_worker_lease(db, lease_name=settings.worker_name, owner_id="worker-1", hostname="host", process_id=1, settings=settings)
        assert lease.owner_id == "worker-1"
        renewed = renew_worker_lease(db, lease_name=settings.worker_name, owner_id="worker-1", settings=settings)
        assert renewed.expires_at > renewed.heartbeat_at
        with pytest.raises(WorkerLeaseActiveError):
            acquire_worker_lease(db, lease_name=settings.worker_name, owner_id="worker-2", hostname="host", process_id=2, settings=settings)

        lease.expires_at = utc_now() - timedelta(seconds=1)
        db.commit()
        reclaimed = acquire_worker_lease(db, lease_name=settings.worker_name, owner_id="worker-2", hostname="host", process_id=2, settings=settings)
        assert reclaimed.owner_id == "worker-2"
        assert release_worker_lease(db, lease_name=settings.worker_name, owner_id="wrong") is False
        assert release_worker_lease(db, lease_name=settings.worker_name, owner_id="worker-2") is True
        assert get_worker_status(db, settings)["status"] == "offline"
    finally:
        db.close()
        generator.close()


def test_worker_status_endpoint_offline(client: TestClient) -> None:
    response = client.get("/api/worker-status")
    assert response.status_code == 200
    assert response.json()["status"] == "offline"

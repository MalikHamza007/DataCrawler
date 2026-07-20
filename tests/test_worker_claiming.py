from datetime import timedelta

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.db.base import utc_now
from app.db.session import get_db
from app.main import app
from app.models.collection_job import CollectionJob
from app.services.collection_jobs import claim_next_job, recover_stale_jobs


def db_from_app() -> object:
    generator = app.dependency_overrides[get_db]()
    return next(generator), generator


def create_job(client: TestClient, name: str = "gulberg") -> dict:
    response = client.post(
        "/api/collection-jobs",
        json={
            "job_type": "places_discovery",
            "city": "Lahore",
            "lahore_zone": "Gulberg",
            "search_config_json": {
                "search_mode": "zone",
                "zone_id": "gulberg",
                "radius_meters": 5000,
                "project_types": ["apartments"],
                "map_center": {"lat": 31.5106, "lng": 74.3441},
            },
        },
    )
    assert response.status_code == 201
    return response.json()


def test_oldest_eligible_job_is_claimed_and_fields_set(client: TestClient) -> None:
    first = create_job(client)
    second = create_job(client)
    db, generator = db_from_app()
    try:
        job = claim_next_job(db, worker_id="worker-1", settings=Settings())
        assert job.id == first["id"]
        assert job.status == "running"
        assert job.worker_id == "worker-1"
        assert job.attempt_count == 1
        assert job.progress_phase == "planning"

        next_job = claim_next_job(db, worker_id="worker-1", settings=Settings())
        assert next_job.id == second["id"]
    finally:
        db.close()
        generator.close()


def test_ineligible_jobs_are_not_claimed_and_stale_recovery(client: TestClient) -> None:
    future = create_job(client)
    cancelled = create_job(client)
    db, generator = db_from_app()
    try:
        future_job = db.get(CollectionJob, future["id"])
        future_job.status = "queued"
        future_job.worker_id = None
        future_job.next_attempt_at = utc_now() + timedelta(hours=1)
        cancelled_job = db.get(type(future_job), cancelled["id"])
        cancelled_job.status = "cancelled"
        db.commit()
        assert claim_next_job(db, worker_id="worker-1", settings=Settings()) is None

        stale = cancelled_job
        stale.status = "running"
        stale.worker_id = "dead-worker"
        stale.attempt_count = 1
        stale.lease_expires_at = utc_now() - timedelta(minutes=5)
        db.commit()
        assert recover_stale_jobs(db, Settings(worker_stale_job_grace_seconds=1)) == 1
        db.refresh(stale)
        assert stale.status == "queued"
        assert stale.worker_id is None
    finally:
        db.close()
        generator.close()

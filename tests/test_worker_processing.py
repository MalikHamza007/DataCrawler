from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.db.base import Base
from app.models.collection_job import CollectionJob
from app.schemas.collection_job import CollectionJobCreate
from app.services.collection_jobs import create_collection_job
from app.workers.runner import LocalWorker


def test_worker_once_processes_dry_run_job_without_google_requests(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'worker.db'}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False}, future=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    Base.metadata.create_all(engine)
    settings = Settings(
        database_url=database_url,
        google_places_dry_run=True,
        google_places_enabled=False,
        worker_poll_interval_seconds=0.01,
        worker_heartbeat_interval_seconds=1,
        worker_lease_seconds=5,
        worker_job_lease_seconds=10,
    )
    with SessionLocal() as db:
        job = create_collection_job(
            db,
            CollectionJobCreate(
                job_type="places_discovery",
                city="Lahore",
                lahore_zone="Gulberg",
                search_config_json={
                    "search_mode": "zone",
                    "zone_id": "gulberg",
                    "radius_meters": 5000,
                    "project_types": ["apartments"],
                    "map_center": {"lat": 31.5106, "lng": 74.3441},
                },
            ),
        )
        job_id = job.id

    result = LocalWorker(settings=settings, session_factory=SessionLocal).start(once=True)
    assert result == 0
    with SessionLocal() as db:
        job = db.get(CollectionJob, job_id)
        assert job.status == "completed"
        assert job.progress_percent == 100
        assert job.worker_id is None
        assert job.execution_summary_json["dry_run"] is True


def test_worker_once_no_job_exits_zero(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'empty-worker.db'}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False}, future=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    Base.metadata.create_all(engine)
    settings = Settings(database_url=database_url, worker_poll_interval_seconds=0.01, worker_heartbeat_interval_seconds=1, worker_lease_seconds=5, worker_job_lease_seconds=10)
    assert LocalWorker(settings=settings, session_factory=SessionLocal).start(once=True) == 0

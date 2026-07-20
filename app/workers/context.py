from __future__ import annotations

from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.models.collection_job import CollectionLog
from app.services.collection_jobs import get_collection_job, heartbeat_job, update_job_progress
from app.workers.exceptions import JobCancellationRequested


class JobExecutionContext:
    def __init__(self, *, session_factory: sessionmaker, job_id: int, worker_id: str, settings: Settings) -> None:
        self.session_factory = session_factory
        self.job_id = job_id
        self.worker_id = worker_id
        self.settings = settings

    def heartbeat(self) -> None:
        with self.session_factory() as db:
            heartbeat_job(db, job_id=self.job_id, worker_id=self.worker_id, settings=self.settings)

    def check_cancelled(self) -> None:
        with self.session_factory() as db:
            job = get_collection_job(db, self.job_id)
            if job.cancel_requested_at is not None:
                raise JobCancellationRequested()

    def update_progress(
        self,
        *,
        phase: str,
        message: str | None = None,
        processed_delta: int = 0,
        created_delta: int = 0,
        updated_delta: int = 0,
        failed_delta: int = 0,
        total_items: int | None = None,
        **_: object,
    ) -> None:
        with self.session_factory() as db:
            job = update_job_progress(
                db,
                job_id=self.job_id,
                worker_id=self.worker_id,
                phase=phase,
                message=message,
                processed_items=processed_delta,
                created_items=created_delta,
                updated_items=updated_delta,
                failed_items=failed_delta,
            )
            if total_items is not None and job.total_items == 0:
                job.total_items = total_items
                db.commit()

    def log(self, level: str, message: str, context: dict | None = None) -> None:
        with self.session_factory() as db:
            db.add(CollectionLog(collection_job_id=self.job_id, level=level, message=message, context_json=context or {}))
            db.commit()

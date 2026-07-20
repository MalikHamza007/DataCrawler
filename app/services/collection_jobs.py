from __future__ import annotations

from datetime import timedelta

from sqlalchemy import or_, select, text
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import ConflictError, EntityNotFoundError, InvalidStatusTransitionError
from app.db.base import utc_now
from app.models.collection_job import CollectionJob, CollectionLog
from app.repositories.collection_jobs import collection_job_repository, collection_log_repository
from app.schemas.collection_job import CollectionJobCreate, CollectionJobUpdate, CollectionLogCreate
from app.schemas.map_config import ProjectSearchConfig
from app.services.lahore_zones import validate_project_search_config

VALID_TRANSITIONS = {
    "queued": {"running", "cancelled"},
    "running": {"completed", "failed", "cancelled"},
    "completed": set(),
    "failed": {"queued"},
    "cancelled": {"queued"},
}


def get_collection_job(db: Session, job_id: int) -> CollectionJob:
    job = collection_job_repository.get(db, job_id)
    if job is None:
        raise EntityNotFoundError(f"Collection job {job_id} was not found.")
    return job


def list_collection_jobs(
    db: Session,
    *,
    offset: int,
    limit: int,
    status: str | None = None,
    job_type: str | None = None,
    lahore_zone: str | None = None,
) -> list[CollectionJob]:
    return collection_job_repository.list(
        db,
        offset=offset,
        limit=limit,
        filters={"status": status, "job_type": job_type, "lahore_zone": lahore_zone},
    )


def create_collection_job(db: Session, payload: CollectionJobCreate) -> CollectionJob:
    data = payload.model_dump()
    if payload.job_type == "places_discovery":
        config = ProjectSearchConfig.model_validate(payload.search_config_json)
        validate_project_search_config(config)
        data["search_config_json"] = config.model_dump(mode="json")
    elif payload.job_type == "website_enrichment":
        raise ValueError("Use a website-enrichment endpoint to create website jobs")
    data["status"] = "queued"
    data["progress_phase"] = "queued"
    data["max_attempts"] = get_settings().worker_max_job_attempts
    return collection_job_repository.create(db, data)


def update_collection_job(db: Session, job_id: int, payload: CollectionJobUpdate) -> CollectionJob:
    job = get_collection_job(db, job_id)
    data = payload.model_dump(exclude_unset=True)
    next_status = data.get("status")
    if next_status is not None and next_status != job.status:
        if next_status not in VALID_TRANSITIONS[job.status]:
            raise InvalidStatusTransitionError(f"Cannot transition collection job from {job.status} to {next_status}.")
        if next_status == "running":
            data["started_at"] = utc_now()
        if next_status in {"completed", "failed", "cancelled"}:
            data["completed_at"] = utc_now()
    return collection_job_repository.update(db, job, data)


def add_collection_log(db: Session, job_id: int, payload: CollectionLogCreate) -> CollectionLog:
    get_collection_job(db, job_id)
    return collection_log_repository.create(db, {"collection_job_id": job_id, **payload.model_dump()})


def delete_collection_job(db: Session, job_id: int) -> None:
    collection_job_repository.delete(db, get_collection_job(db, job_id))


def list_collection_logs(db: Session, job_id: int, *, offset: int = 0, limit: int = 100, level: str | None = None) -> list[CollectionLog]:
    get_collection_job(db, job_id)
    stmt = select(CollectionLog).where(CollectionLog.collection_job_id == job_id)
    if level:
        stmt = stmt.where(CollectionLog.level == level)
    stmt = stmt.order_by(CollectionLog.created_at.asc(), CollectionLog.id.asc()).offset(offset).limit(min(limit, 500))
    return list(db.scalars(stmt).all())


def cancel_collection_job(db: Session, job_id: int) -> CollectionJob:
    job = get_collection_job(db, job_id)
    now = utc_now()
    if job.status == "queued":
        job.status = "cancelled"
        job.cancel_requested_at = now
        job.completed_at = now
        job.progress_phase = "cancelled"
        job.progress_message = "Cancelled before collection started"
        _add_log(db, job.id, "info", "Job cancelled before collection started")
    elif job.status == "running":
        job.cancel_requested_at = now
        job.progress_phase = "cancelling"
        job.progress_message = "Cancellation requested"
        _add_log(db, job.id, "info", "Cancellation requested")
    else:
        raise ConflictError(f"Collection job {job.id} cannot be cancelled from status {job.status}.")
    db.commit()
    db.refresh(job)
    return job


def retry_collection_job(db: Session, job_id: int) -> CollectionJob:
    job = get_collection_job(db, job_id)
    if job.status not in {"failed", "cancelled"}:
        raise ConflictError(f"Collection job {job.id} cannot be retried from status {job.status}.")
    if job.attempt_count >= job.max_attempts:
        raise ConflictError("Collection job has reached maximum attempts.")
    job.status = "queued"
    job.next_attempt_at = None
    job.cancel_requested_at = None
    job.claimed_at = None
    job.heartbeat_at = None
    job.lease_expires_at = None
    job.worker_id = None
    job.completed_at = None
    job.progress_phase = "queued"
    job.progress_message = "Queued for manual retry"
    job.error_message = None
    job.last_error_type = None
    job.last_error_retryable = None
    _add_log(db, job.id, "info", "Job queued for manual retry")
    db.commit()
    db.refresh(job)
    return job


def claim_next_job(db: Session, *, worker_id: str, settings: Settings | None = None, job_id: int | None = None) -> CollectionJob | None:
    settings = settings or get_settings()
    _begin_immediate(db)
    now = utc_now()
    stmt = (
        select(CollectionJob)
        .where(
            CollectionJob.status == "queued",
            CollectionJob.job_type.in_(settings.worker_supported_job_types),
            CollectionJob.cancel_requested_at.is_(None),
            CollectionJob.attempt_count < CollectionJob.max_attempts,
            or_(CollectionJob.next_attempt_at.is_(None), CollectionJob.next_attempt_at <= now),
        )
        .order_by(CollectionJob.created_at.asc(), CollectionJob.id.asc())
        .limit(1)
    )
    if job_id is not None:
        stmt = stmt.where(CollectionJob.id == job_id)
    job = db.scalar(stmt)
    if job is None:
        return None
    job.status = "running"
    job.worker_id = worker_id
    job.claimed_at = now
    job.heartbeat_at = now
    job.lease_expires_at = now + timedelta(seconds=settings.worker_job_lease_seconds)
    job.attempt_count += 1
    job.started_at = job.started_at or now
    job.progress_phase = "planning"
    job.progress_message = "Planning collection job"
    _add_log(db, job.id, "info", "Job claimed by local worker", {"worker_id": _redact(worker_id)})
    db.commit()
    db.refresh(job)
    return job


def heartbeat_job(db: Session, *, job_id: int, worker_id: str, settings: Settings | None = None) -> CollectionJob:
    settings = settings or get_settings()
    job = get_collection_job(db, job_id)
    if job.worker_id != worker_id or job.status != "running":
        raise ConflictError("Job ownership was lost.")
    now = utc_now()
    job.heartbeat_at = now
    job.lease_expires_at = now + timedelta(seconds=settings.worker_job_lease_seconds)
    db.commit()
    db.refresh(job)
    return job


def update_job_progress(db: Session, *, job_id: int, worker_id: str, phase: str, message: str | None = None, **counters: int) -> CollectionJob:
    job = heartbeat_job(db, job_id=job_id, worker_id=worker_id)
    job.progress_phase = phase
    if message is not None:
        job.progress_message = message
    for field, delta in counters.items():
        if delta:
            setattr(job, field, getattr(job, field) + delta)
    db.commit()
    db.refresh(job)
    return job


def finalize_completed_job(db: Session, *, job_id: int, worker_id: str, summary: dict | None = None) -> CollectionJob:
    job = heartbeat_job(db, job_id=job_id, worker_id=worker_id)
    job.status = "completed"
    job.completed_at = utc_now()
    job.progress_phase = "completed"
    job.progress_message = "Collection completed"
    job.execution_summary_json = summary or job.execution_summary_json
    job.worker_id = None
    job.lease_expires_at = None
    _add_log(db, job.id, "info", "Job completed")
    db.commit()
    db.refresh(job)
    return job


def finalize_cancelled_job(db: Session, *, job_id: int, worker_id: str) -> CollectionJob:
    job = get_collection_job(db, job_id)
    if job.worker_id != worker_id:
        raise ConflictError("Job ownership was lost.")
    job.status = "cancelled"
    job.completed_at = utc_now()
    job.progress_phase = "cancelled"
    job.progress_message = "Collection cancelled by operator"
    job.worker_id = None
    job.lease_expires_at = None
    _add_log(db, job.id, "info", "Job cancelled by operator")
    db.commit()
    db.refresh(job)
    return job


def schedule_retry_or_fail(db: Session, *, job_id: int, worker_id: str, exc: Exception, retryable: bool, settings: Settings | None = None) -> CollectionJob:
    settings = settings or get_settings()
    job = get_collection_job(db, job_id)
    if job.worker_id != worker_id:
        raise ConflictError("Job ownership was lost.")
    now = utc_now()
    job.last_error_type = exc.__class__.__name__
    job.last_error_retryable = retryable
    job.error_message = str(exc) or exc.__class__.__name__
    job.worker_id = None
    job.heartbeat_at = None
    job.lease_expires_at = None
    if retryable and job.attempt_count < job.max_attempts:
        delay = min(settings.worker_retry_base_delay_seconds * (2 ** max(job.attempt_count - 1, 0)), settings.worker_retry_max_delay_seconds)
        job.status = "queued"
        job.next_attempt_at = now + timedelta(seconds=delay)
        job.progress_phase = "retry_wait"
        job.progress_message = "Retry scheduled after temporary failure"
        _add_log(db, job.id, "warning", "Retry scheduled after temporary failure", {"delay_seconds": delay})
    else:
        job.status = "failed"
        job.completed_at = now
        job.progress_phase = "failed"
        job.progress_message = "Collection failed"
        _add_log(db, job.id, "error", "Job failed", {"error_type": job.last_error_type, "retryable": retryable})
    db.commit()
    db.refresh(job)
    return job


def recover_stale_jobs(db: Session, settings: Settings | None = None) -> int:
    settings = settings or get_settings()
    cutoff = utc_now() - timedelta(seconds=settings.worker_stale_job_grace_seconds)
    jobs = list(db.scalars(select(CollectionJob).where(CollectionJob.status == "running", CollectionJob.lease_expires_at < cutoff)).all())
    for job in jobs:
        job.worker_id = None
        job.heartbeat_at = None
        job.lease_expires_at = None
        job.last_error_type = "WorkerLeaseExpired"
        job.last_error_retryable = True
        if job.attempt_count < job.max_attempts:
            job.status = "queued"
            job.next_attempt_at = utc_now()
            job.progress_phase = "queued"
            job.progress_message = "Requeued after interrupted worker execution"
            _add_log(db, job.id, "warning", "Stale running job requeued")
        else:
            job.status = "failed"
            job.completed_at = utc_now()
            job.progress_phase = "failed"
            job.progress_message = "Worker stopped and maximum attempts were reached"
            _add_log(db, job.id, "error", "Stale running job failed after maximum attempts")
    db.commit()
    return len(jobs)


def _add_log(db: Session, job_id: int, level: str, message: str, context: dict | None = None) -> None:
    db.add(CollectionLog(collection_job_id=job_id, level=level, message=message, context_json=context or {}))


def _redact(value: str) -> str:
    return value[:12] + "..." if len(value) > 12 else value


def _begin_immediate(db: Session) -> None:
    bind = db.get_bind()
    if bind.dialect.name == "sqlite" and not db.in_transaction():
        db.execute(text("BEGIN IMMEDIATE"))

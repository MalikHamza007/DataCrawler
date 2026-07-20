from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.base import utc_now
from app.models.collection_job import CollectionJob
from app.models.worker_lease import WorkerLease


class WorkerLeaseActiveError(Exception):
    pass


def acquire_worker_lease(
    db: Session,
    *,
    lease_name: str,
    owner_id: str,
    hostname: str,
    process_id: int,
    settings: Settings | None = None,
) -> WorkerLease:
    settings = settings or get_settings()
    _begin_immediate(db)
    now = utc_now()
    lease = db.scalar(select(WorkerLease).where(WorkerLease.lease_name == lease_name))
    if lease and lease.owner_id and lease.owner_id != owner_id and lease.expires_at and _after(lease.expires_at, now):
        raise WorkerLeaseActiveError("Another Alduor local worker is already active.")
    if lease is None:
        lease = WorkerLease(lease_name=lease_name)
        db.add(lease)
    lease.owner_id = owner_id
    lease.hostname = hostname
    lease.process_id = process_id
    lease.started_at = now
    lease.heartbeat_at = now
    lease.expires_at = now + timedelta(seconds=settings.worker_lease_seconds)
    db.commit()
    db.refresh(lease)
    return lease


def renew_worker_lease(db: Session, *, lease_name: str, owner_id: str, settings: Settings | None = None) -> WorkerLease:
    settings = settings or get_settings()
    _begin_immediate(db)
    lease = db.scalar(select(WorkerLease).where(WorkerLease.lease_name == lease_name))
    if lease is None or lease.owner_id != owner_id:
        raise WorkerLeaseActiveError("Worker lease ownership was lost.")
    now = utc_now()
    lease.heartbeat_at = now
    lease.expires_at = now + timedelta(seconds=settings.worker_lease_seconds)
    db.commit()
    db.refresh(lease)
    return lease


def release_worker_lease(db: Session, *, lease_name: str, owner_id: str) -> bool:
    lease = db.scalar(select(WorkerLease).where(WorkerLease.lease_name == lease_name))
    if lease is None or lease.owner_id != owner_id:
        return False
    lease.owner_id = None
    lease.expires_at = utc_now()
    db.commit()
    return True


def get_worker_status(db: Session, settings: Settings | None = None) -> dict:
    settings = settings or get_settings()
    now = utc_now()
    lease = db.scalar(select(WorkerLease).where(WorkerLease.lease_name == settings.worker_name))
    if lease is None or not lease.owner_id or not lease.expires_at or not _after(lease.expires_at, now):
        return {
            "worker_name": settings.worker_name,
            "status": "offline",
            "heartbeat_at": lease.heartbeat_at if lease else None,
            "current_job_id": None,
        }
    current_job = db.scalar(select(CollectionJob).where(CollectionJob.worker_id == lease.owner_id, CollectionJob.status == "running"))
    return {
        "worker_name": settings.worker_name,
        "status": "online",
        "owner_id": _redact_owner(lease.owner_id),
        "hostname": lease.hostname,
        "process_id": lease.process_id,
        "started_at": lease.started_at,
        "heartbeat_at": lease.heartbeat_at,
        "expires_at": lease.expires_at,
        "current_job_id": current_job.id if current_job else None,
    }


def _redact_owner(owner_id: str) -> str:
    if len(owner_id) <= 12:
        return owner_id
    return f"{owner_id[:12]}..."


def _after(left: object, right: object) -> bool:
    if hasattr(left, "tzinfo") and hasattr(right, "tzinfo"):
        if left.tzinfo is None and right.tzinfo is not None:
            right = right.replace(tzinfo=None)
        if left.tzinfo is not None and right.tzinfo is None:
            left = left.replace(tzinfo=None)
    return left > right


def _begin_immediate(db: Session) -> None:
    bind = db.get_bind()
    if bind.dialect.name == "sqlite" and not db.in_transaction():
        db.execute(text("BEGIN IMMEDIATE"))

from __future__ import annotations

from fastapi import APIRouter

from app.api.dependencies import DbSession
from app.schemas.worker_status import WorkerStatusRead
from app.services.worker_leases import get_worker_status

router = APIRouter(tags=["Worker Status"])


@router.get("/worker-status", response_model=WorkerStatusRead)
def worker_status(db: DbSession) -> dict:
    return get_worker_status(db)

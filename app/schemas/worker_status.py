from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class WorkerStatusRead(BaseModel):
    worker_name: str
    status: str
    owner_id: str | None = None
    hostname: str | None = None
    process_id: int | None = None
    started_at: datetime | None = None
    heartbeat_at: datetime | None = None
    expires_at: datetime | None = None
    current_job_id: int | None = None

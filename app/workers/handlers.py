from __future__ import annotations

from typing import Protocol

from app.workers.context import JobExecutionContext


class JobHandler(Protocol):
    def execute(self, job_id: int, context: JobExecutionContext) -> dict:
        ...

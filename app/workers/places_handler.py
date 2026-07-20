from __future__ import annotations

from sqlalchemy.orm import sessionmaker

from app.collectors.google_places.exceptions import (
    GooglePlacesConfigurationError,
    GooglePlacesInvalidRequestError,
    GooglePlacesPermissionError,
    SearchGeometryError,
    SearchPlanLimitError,
)
from app.core.config import Settings
from app.services.places_discovery import discover_places_for_job
from app.services.website_enrichment import queue_for_places_job
from app.workers.context import JobExecutionContext


class PlacesDiscoveryJobHandler:
    def __init__(self, *, session_factory: sessionmaker, settings: Settings) -> None:
        self.session_factory = session_factory
        self.settings = settings

    def execute(self, job_id: int, context: JobExecutionContext) -> dict:
        with self.session_factory() as db:
            result = discover_places_for_job(
                db,
                job_id,
                settings=self.settings,
                progress_callback=context.update_progress,
                heartbeat_callback=context.heartbeat,
                cancellation_check=context.check_cancelled,
                manage_status=False,
            )
            summary = result.model_dump()
            if not result.dry_run:
                child_job_ids = queue_for_places_job(db, job_id, self.settings)
                summary["website_jobs_queued"] = len(child_job_ids)
                summary["website_job_ids"] = child_job_ids
        return summary


TERMINAL_EXCEPTIONS = (
    GooglePlacesConfigurationError,
    GooglePlacesInvalidRequestError,
    GooglePlacesPermissionError,
    SearchGeometryError,
    SearchPlanLimitError,
    ValueError,
)

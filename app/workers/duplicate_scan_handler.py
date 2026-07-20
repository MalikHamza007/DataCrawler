from __future__ import annotations

from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.intelligence.duplicates import scan_duplicates
from app.models.collection_job import CollectionJob
from app.workers.context import JobExecutionContext


class DuplicateScanJobHandler:
    def __init__(self, *, session_factory: sessionmaker, settings: Settings) -> None:
        self.session_factory = session_factory; self.settings = settings

    def execute(self, job_id: int, context: JobExecutionContext) -> dict:
        with self.session_factory() as db:
            job = db.get(CollectionJob, job_id); config = dict(job.search_config_json or {})
        context.update_progress(phase="building_blocks", message=f"Generating {config.get('entity_type')} duplicate blocks")
        with self.session_factory() as db:
            return scan_duplicates(db, config["entity_type"], self.settings, config.get("lahore_zone"), config.get("minimum_score"), context.check_cancelled, context.update_progress)

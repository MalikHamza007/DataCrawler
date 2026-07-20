from __future__ import annotations

from app.core.config import Settings
from app.services.collection_jobs import get_collection_job
from app.services.exports import generate_export_artifact
from app.workers.context import JobExecutionContext


class ExportGenerationJobHandler:
    def __init__(self, session_factory, settings: Settings):
        self.session_factory = session_factory
        self.settings = settings

    def execute(self, job_id: int, context: JobExecutionContext) -> dict:
        with self.session_factory() as db:
            job = get_collection_job(db, job_id)
            artifact_id = (job.search_config_json or {}).get("export_artifact_id")
            if not artifact_id:
                raise ValueError("Export job is missing export_artifact_id.")
            artifact = generate_export_artifact(db, int(artifact_id), self.settings, context)
            db.commit()
            return {
                "export_artifact_id": artifact.id,
                "format": artifact.format,
                "scope": artifact.scope,
                "filename": artifact.filename,
                "row_count": artifact.row_count,
                "file_size_bytes": artifact.file_size_bytes,
                "sha256": artifact.sha256,
            }

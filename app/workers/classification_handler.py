from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.intelligence.classification import assess_developer, assess_project
from app.intelligence.relationships import score_relationship
from app.models.collection_job import CollectionJob
from app.models.developer import Developer
from app.models.project import Project
from app.models.project_developer_relationship import ProjectDeveloperRelationship
from app.models.intelligence import ClassificationAssessment
from app.services.refinement import finalize_refinement
from app.workers.context import JobExecutionContext


class ClassificationAnalysisJobHandler:
    def __init__(self, *, session_factory: sessionmaker, settings: Settings) -> None:
        self.session_factory = session_factory; self.settings = settings

    def execute(self, job_id: int, context: JobExecutionContext) -> dict:
        with self.session_factory() as db:
            job = db.get(CollectionJob, job_id); config = job.search_config_json or {}; entity_type = config.get("entity_type", "all"); requested = set(config.get("entity_ids") or [])
            developer_ids = list(db.scalars(select(Developer.id).where(Developer.record_status == "active")).all()) if entity_type in {"developer", "all"} else []
            project_ids = list(db.scalars(select(Project.id).where(Project.record_status == "active")).all()) if entity_type in {"project", "all"} else []
            relationship_ids = list(db.scalars(select(ProjectDeveloperRelationship.id)).all()) if entity_type in {"relationship", "all"} else []
        if requested:
            developer_ids = [value for value in developer_ids if value in requested]; project_ids = [value for value in project_ids if value in requested]; relationship_ids = [value for value in relationship_ids if value in requested]
        total = len(developer_ids) + len(project_ids) + len(relationship_ids); context.update_progress(phase="loading_evidence", message="Loading classification evidence", total_items=total)
        summary = {"developers_processed": 0, "projects_processed": 0, "relationships_processed": 0, "assessments_created": 0, "assessments_updated": 0, "manual_decisions_preserved": 0, "insufficient_evidence": 0}
        for entity, ids in (("developer", developer_ids), ("project", project_ids), ("relationship", relationship_ids)):
            for index, entity_id in enumerate(ids, 1):
                context.check_cancelled()
                with self.session_factory() as db:
                    existed = False
                    if entity != "relationship":
                        owner = ClassificationAssessment.developer_id if entity == "developer" else ClassificationAssessment.project_id
                        existed = db.scalar(select(ClassificationAssessment.id).where(ClassificationAssessment.entity_type == entity, owner == entity_id, ClassificationAssessment.rule_version == self.settings.intelligence_rule_version)) is not None
                    if entity == "developer": result = assess_developer(db, entity_id, self.settings); summary["developers_processed"] += 1
                    elif entity == "project": result = assess_project(db, entity_id, self.settings); summary["projects_processed"] += 1
                    else: result = score_relationship(db, entity_id, self.settings); summary["relationships_processed"] += 1
                    if entity != "relationship":
                        summary["assessments_updated" if existed else "assessments_created"] += 1
                        if result.manually_reviewed: summary["manual_decisions_preserved"] += 1
                        if result.confidence_level == "insufficient_evidence": summary["insufficient_evidence"] += 1
                context.update_progress(phase="classifying" if entity != "relationship" else "scoring_relationships", message=f"Processing {entity} {index} of {len(ids)}", processed_delta=1)
        if config.get("refine_clean_data"):
            context.update_progress(phase="refining", message="Building strict Alduor-ready records")
            with self.session_factory() as db:
                summary["refinement"] = finalize_refinement(db, self.settings)
        return summary

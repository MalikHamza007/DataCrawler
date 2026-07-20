from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.collection_job import CollectionJob
from app.services.collection_jobs import get_collection_job


def get_research_summary(db: Session, parent_job_id: int) -> dict[str, object]:
    parent = get_collection_job(db, parent_job_id)
    children = [
        job for job in db.scalars(select(CollectionJob).where(CollectionJob.job_type == "website_enrichment")).all()
        if (job.search_config_json or {}).get("parent_collection_job_id") == parent_job_id
    ]
    parent_summary = dict(parent.execution_summary_json or {})
    child_summaries = [dict(job.execution_summary_json or {}) for job in children]
    pending = sum(job.status in {"queued", "running"} for job in children)
    failed_statuses = {"failed", "cancelled"}
    failed = int(parent.status in failed_statuses) + sum(job.status in failed_statuses for job in children)
    places_requests = parent_summary.get(
        "requests_made",
        parent_summary.get("api_requests", parent.processed_items if parent.status == "running" else 0),
    )
    pages_visited = sum(
        summary.get("pages_selected", job.processed_items)
        for job, summary in zip(children, child_summaries, strict=True)
    )
    if parent.status in {"queued", "running"} or pending:
        status = "running"
    elif parent.status == "failed":
        status = "failed"
    elif parent.status == "cancelled":
        status = "cancelled"
    else:
        status = "completed_with_errors" if failed else "completed"
    return {
        "parent_job_id": parent_job_id,
        "status": status,
        "places": {
            "api_requests": places_requests,
            "raw_results": parent_summary.get("raw_results", 0),
            "unique_results": parent_summary.get("unique_place_ids", 0),
            "duplicates_skipped": parent_summary.get("duplicates_skipped", 0),
            "official_websites_found": parent_summary.get("websites_discovered", 0),
        },
        "websites": {
            "queued": len(children),
            "pending": pending,
            "completed": sum(job.status == "completed" for job in children),
            "failed": sum(job.status in failed_statuses for job in children),
            "pages_visited": pages_visited,
        },
        "results": {
            "projects_created": parent_summary.get("projects_created", 0) + sum(item.get("projects_created", 0) for item in child_summaries),
            "projects_updated": parent_summary.get("projects_updated", 0),
            "developers_created": sum(item.get("developers_created", 0) for item in child_summaries),
            "contacts_created": parent_summary.get("contacts_created", 0) + sum(item.get("contacts_created", 0) for item in child_summaries),
            "social_profiles_created": sum(item.get("social_profiles_created", 0) for item in child_summaries),
            "evidence_records_created": sum(item.get("evidence_records_created", 0) for item in child_summaries),
        },
        "resources_processed": places_requests + pages_visited,
        "errors": failed,
        "child_job_ids": [job.id for job in children],
    }

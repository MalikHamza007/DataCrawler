from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.services.refinement import queue_refinement, refinement_summary


router = APIRouter(prefix="/refinement", tags=["Data Refinement"])


@router.get("/summary")
def get_refinement_summary(db: Session = Depends(get_db)) -> dict:
    return refinement_summary(db)


@router.post("/jobs", status_code=201)
def create_refinement_job(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    job, queued = queue_refinement(db, settings)
    return {
        "refinement_job_id": job.id,
        "status": job.status,
        **queued,
    }

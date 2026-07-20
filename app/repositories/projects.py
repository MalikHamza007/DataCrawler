from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.project import Project
from app.repositories.base import Repository


class ProjectRepository(Repository[Project]):
    def get_by_google_place_id(self, db: Session, google_place_id: str) -> Project | None:
        return db.scalar(select(Project).where(Project.google_place_id == google_place_id))


project_repository = ProjectRepository(Project)

from __future__ import annotations

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now


class ProjectDiscovery(Base):
    __tablename__ = "project_discoveries"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    collection_job_id: Mapped[int] = mapped_column(ForeignKey("collection_jobs.id", ondelete="CASCADE"), index=True)
    source: Mapped[str] = mapped_column(String(50), default="google_places", index=True)
    source_method: Mapped[str] = mapped_column(String(50), index=True)
    source_query: Mapped[str | None] = mapped_column(String(500))
    source_cell_id: Mapped[str | None] = mapped_column(String(100), index=True)
    google_primary_type: Mapped[str | None] = mapped_column(String(100))
    google_types_json: Mapped[list | None] = mapped_column(JSON)
    google_business_status: Mapped[str | None] = mapped_column(String(100))
    encounter_count: Mapped[int] = mapped_column(Integer, default=1)
    first_discovered_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    last_discovered_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    project = relationship("Project")
    collection_job = relationship("CollectionJob")

from __future__ import annotations

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now


class SourceEvidence(Base):
    __tablename__ = "source_evidence"
    __table_args__ = (
        CheckConstraint(
            "developer_id IS NOT NULL OR project_id IS NOT NULL OR collection_job_id IS NOT NULL",
            name="ck_source_evidence_at_least_one_owner",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    developer_id: Mapped[int | None] = mapped_column(ForeignKey("developers.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    collection_job_id: Mapped[int | None] = mapped_column(ForeignKey("collection_jobs.id", ondelete="CASCADE"), index=True)
    source_type: Mapped[str] = mapped_column(String(50), index=True)
    source_url: Mapped[str] = mapped_column(String(2048))
    source_title: Mapped[str | None] = mapped_column(String(255))
    captured_text: Mapped[str | None] = mapped_column(Text)
    field_name: Mapped[str | None] = mapped_column(String(255))
    extracted_value: Mapped[str | None] = mapped_column(String(2048))
    verification_status: Mapped[str] = mapped_column(String(50), default="unverified", index=True)
    collected_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    developer = relationship("Developer", back_populates="evidence")
    project = relationship("Project", back_populates="evidence")
    collection_job = relationship("CollectionJob", back_populates="evidence")

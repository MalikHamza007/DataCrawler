from __future__ import annotations

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now


class FieldVerification(Base):
    __tablename__ = "field_verifications"
    __table_args__ = (
        CheckConstraint(
            "(developer_id IS NOT NULL AND project_id IS NULL) OR (developer_id IS NULL AND project_id IS NOT NULL)",
            name="ck_field_verifications_exactly_one_owner",
        ),
        Index("ix_field_verifications_developer_id", "developer_id"),
        Index("ix_field_verifications_project_id", "project_id"),
        Index("ix_field_verifications_field_name", "field_name"),
        Index("ix_field_verifications_status", "verification_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    developer_id: Mapped[int | None] = mapped_column(ForeignKey("developers.id", ondelete="CASCADE"))
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    verified_value: Mapped[str] = mapped_column(String(2048), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(50), nullable=False)
    source_evidence_id: Mapped[int | None] = mapped_column(ForeignKey("source_evidence.id", ondelete="SET NULL"))
    review_note: Mapped[str | None] = mapped_column(Text)
    verified_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    developer = relationship("Developer")
    project = relationship("Project")
    source_evidence = relationship("SourceEvidence")


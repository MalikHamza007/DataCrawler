from __future__ import annotations

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now


class ReviewEvent(Base):
    __tablename__ = "review_events"
    __table_args__ = (
        CheckConstraint(
            "developer_id IS NOT NULL OR project_id IS NOT NULL OR social_capture_id IS NOT NULL OR classification_assessment_id IS NOT NULL OR relationship_id IS NOT NULL OR duplicate_candidate_id IS NOT NULL",
            name="ck_review_events_at_least_one_entity",
        ),
        Index("ix_review_events_developer_id", "developer_id"),
        Index("ix_review_events_project_id", "project_id"),
        Index("ix_review_events_action_type", "action_type"),
        Index("ix_review_events_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    developer_id: Mapped[int | None] = mapped_column(ForeignKey("developers.id", ondelete="SET NULL"))
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"))
    social_capture_id: Mapped[int | None] = mapped_column(ForeignKey("social_captures.id", ondelete="SET NULL"))
    classification_assessment_id: Mapped[int | None] = mapped_column(ForeignKey("classification_assessments.id", ondelete="SET NULL"))
    relationship_id: Mapped[int | None] = mapped_column(ForeignKey("project_developer_relationships.id", ondelete="SET NULL"))
    duplicate_candidate_id: Mapped[int | None] = mapped_column(ForeignKey("duplicate_candidates.id", ondelete="SET NULL"))
    action_type: Mapped[str] = mapped_column(String(80), nullable=False)
    before_json: Mapped[str | None] = mapped_column(Text)
    after_json: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    operator_label: Mapped[str] = mapped_column(String(255), default="Local Operator", nullable=False)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    developer = relationship("Developer")
    project = relationship("Project")


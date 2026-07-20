from __future__ import annotations

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now


class ClassificationAssessment(Base):
    __tablename__ = "classification_assessments"
    __table_args__ = (
        CheckConstraint("(developer_id IS NOT NULL AND project_id IS NULL) OR (developer_id IS NULL AND project_id IS NOT NULL)", name="ck_assessment_one_owner"),
        UniqueConstraint("entity_type", "developer_id", "project_id", "rule_version", name="uq_assessment_entity_rule"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    developer_id: Mapped[int | None] = mapped_column(ForeignKey("developers.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    entity_type: Mapped[str] = mapped_column(String(50), index=True)
    suggested_classification: Mapped[str] = mapped_column(String(50), index=True)
    system_score: Mapped[int] = mapped_column(Integer, index=True)
    confidence_level: Mapped[str] = mapped_column(String(50), index=True)
    signals_json: Mapped[list] = mapped_column(JSON, default=list)
    explanation: Mapped[str] = mapped_column(Text)
    rule_version: Mapped[str] = mapped_column(String(50), index=True)
    assessment_status: Mapped[str] = mapped_column(String(50), default="pending_review", index=True)
    manual_classification: Mapped[str | None] = mapped_column(String(50))
    manual_note: Mapped[str | None] = mapped_column(Text)
    manually_reviewed: Mapped[bool] = mapped_column(default=False)
    reviewed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    developer = relationship("Developer", back_populates="classification_assessments")
    project = relationship("Project", back_populates="classification_assessments")

    @property
    def effective_classification(self) -> str:
        return self.manual_classification or self.suggested_classification


class DuplicateCandidate(Base):
    __tablename__ = "duplicate_candidates"
    __table_args__ = (
        CheckConstraint("(entity_type = 'developer' AND left_developer_id IS NOT NULL AND right_developer_id IS NOT NULL AND left_project_id IS NULL AND right_project_id IS NULL AND left_developer_id < right_developer_id) OR (entity_type = 'project' AND left_project_id IS NOT NULL AND right_project_id IS NOT NULL AND left_developer_id IS NULL AND right_developer_id IS NULL AND left_project_id < right_project_id)", name="ck_duplicate_valid_ordered_pair"),
        UniqueConstraint("entity_type", "left_developer_id", "right_developer_id", "left_project_id", "right_project_id", "rule_version", name="uq_duplicate_pair_rule"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(50), index=True)
    left_developer_id: Mapped[int | None] = mapped_column(ForeignKey("developers.id", ondelete="CASCADE"))
    right_developer_id: Mapped[int | None] = mapped_column(ForeignKey("developers.id", ondelete="CASCADE"))
    left_project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    right_project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    duplicate_score: Mapped[int] = mapped_column(Integer, index=True)
    confidence_level: Mapped[str] = mapped_column(String(50), index=True)
    signals_json: Mapped[list] = mapped_column(JSON, default=list)
    explanation: Mapped[str] = mapped_column(Text)
    rule_version: Mapped[str] = mapped_column(String(50), index=True)
    status: Mapped[str] = mapped_column(String(50), default="pending", index=True)
    review_note: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    merge_operation_id: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class MergeOperation(Base):
    __tablename__ = "merge_operations"
    __table_args__ = (
        CheckConstraint("(entity_type = 'developer' AND survivor_developer_id IS NOT NULL AND absorbed_developer_id IS NOT NULL AND survivor_project_id IS NULL AND absorbed_project_id IS NULL AND survivor_developer_id <> absorbed_developer_id) OR (entity_type = 'project' AND survivor_project_id IS NOT NULL AND absorbed_project_id IS NOT NULL AND survivor_developer_id IS NULL AND absorbed_developer_id IS NULL AND survivor_project_id <> absorbed_project_id)", name="ck_merge_valid_pair"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(50), index=True)
    survivor_developer_id: Mapped[int | None] = mapped_column(ForeignKey("developers.id", ondelete="SET NULL"))
    absorbed_developer_id: Mapped[int | None] = mapped_column(ForeignKey("developers.id", ondelete="SET NULL"))
    survivor_project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"))
    absorbed_project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"))
    duplicate_candidate_id: Mapped[int | None] = mapped_column(ForeignKey("duplicate_candidates.id", ondelete="SET NULL"), index=True)
    preview_json: Mapped[dict] = mapped_column(JSON)
    actions_json: Mapped[dict | None] = mapped_column(JSON)
    conflicts_json: Mapped[dict | None] = mapped_column(JSON)
    operator_note: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="previewed", index=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))

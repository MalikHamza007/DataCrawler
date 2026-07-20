from __future__ import annotations

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now


class ProjectDeveloperRelationship(Base):
    __tablename__ = "project_developer_relationships"
    __table_args__ = (
        UniqueConstraint("project_id", "developer_id", "relationship_type", "source_url", name="uq_project_developer_candidate"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    developer_id: Mapped[int] = mapped_column(ForeignKey("developers.id", ondelete="CASCADE"), index=True)
    relationship_type: Mapped[str] = mapped_column(String(50), default="unknown")
    status: Mapped[str] = mapped_column(String(50), default="candidate", index=True)
    source_evidence_id: Mapped[int | None] = mapped_column(ForeignKey("source_evidence.id", ondelete="SET NULL"), index=True)
    source_url: Mapped[str] = mapped_column(String(2048))
    evidence_text: Mapped[str] = mapped_column(Text)
    system_score: Mapped[int | None] = mapped_column(Integer)
    confidence_level: Mapped[str | None] = mapped_column(String(50), index=True)
    signals_json: Mapped[list | None] = mapped_column(JSON)
    explanation: Mapped[str | None] = mapped_column(Text)
    rule_version: Mapped[str | None] = mapped_column(String(50), index=True)
    evaluated_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    reviewed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    review_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    project = relationship("Project", back_populates="relationship_candidates")
    developer = relationship("Developer", back_populates="relationship_candidates")
    source_evidence = relationship("SourceEvidence")

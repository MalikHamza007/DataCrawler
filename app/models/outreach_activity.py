from __future__ import annotations

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now


class OutreachActivity(Base):
    __tablename__ = "outreach_activities"
    __table_args__ = (
        CheckConstraint(
            "(developer_id IS NOT NULL AND project_id IS NULL) OR (developer_id IS NULL AND project_id IS NOT NULL)",
            name="ck_outreach_activities_exactly_one_owner",
        ),
        Index("ix_outreach_activities_developer_id", "developer_id"),
        Index("ix_outreach_activities_project_id", "project_id"),
        Index("ix_outreach_activities_activity_type", "activity_type"),
        Index("ix_outreach_activities_channel", "channel"),
        Index("ix_outreach_activities_occurred_at", "occurred_at"),
        Index("ix_outreach_activities_follow_up_at", "follow_up_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    developer_id: Mapped[int | None] = mapped_column(ForeignKey("developers.id", ondelete="CASCADE"))
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    activity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    direction: Mapped[str] = mapped_column(String(50), nullable=False)
    status_after: Mapped[str | None] = mapped_column(String(50))
    contact_value: Mapped[str | None] = mapped_column(String(2048))
    contact_person: Mapped[str | None] = mapped_column(String(255))
    note: Mapped[str | None] = mapped_column(Text)
    follow_up_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    occurred_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    developer = relationship("Developer")
    project = relationship("Project")


from __future__ import annotations

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now


class SocialProfile(Base):
    __tablename__ = "social_profiles"
    __table_args__ = (
        CheckConstraint(
            "(developer_id IS NOT NULL AND project_id IS NULL) OR (developer_id IS NULL AND project_id IS NOT NULL)",
            name="ck_social_profiles_exactly_one_owner",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    developer_id: Mapped[int | None] = mapped_column(ForeignKey("developers.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    platform: Mapped[str] = mapped_column(String(50), index=True)
    profile_name: Mapped[str | None] = mapped_column(String(255))
    profile_url: Mapped[str] = mapped_column(String(2048))
    normalized_url: Mapped[str | None] = mapped_column(String(2048), index=True)
    is_official: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_status: Mapped[str] = mapped_column(String(50), default="unverified")
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    developer = relationship("Developer", back_populates="social_profiles")
    project = relationship("Project", back_populates="social_profiles")

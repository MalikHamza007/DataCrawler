from __future__ import annotations

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now


class SocialCapture(Base):
    __tablename__ = "social_captures"
    __table_args__ = (
        Index("ix_social_captures_platform", "platform"),
        Index("ix_social_captures_page_kind", "page_kind"),
        Index("ix_social_captures_review_status", "review_status"),
        Index("ix_social_captures_content_hash", "content_hash"),
        Index("ix_social_captures_canonical_url", "canonical_url"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    page_kind: Mapped[str] = mapped_column(String(80), nullable=False)
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    canonical_url: Mapped[str | None] = mapped_column(String(2048))
    page_title: Mapped[str | None] = mapped_column(String(255))
    profile_name: Mapped[str | None] = mapped_column(String(255))
    username: Mapped[str | None] = mapped_column(String(255))
    visible_text_excerpt: Mapped[str | None] = mapped_column(Text)
    about_text: Mapped[str | None] = mapped_column(Text)
    capture_payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    extractor_version: Mapped[str] = mapped_column(String(80), nullable=False)
    capture_version: Mapped[str] = mapped_column(String(20), nullable=False)
    extension_version: Mapped[str | None] = mapped_column(String(50))
    developer_id: Mapped[int | None] = mapped_column(ForeignKey("developers.id", ondelete="SET NULL"), index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), index=True)
    review_status: Mapped[str] = mapped_column(String(50), default="unassigned")
    captured_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    reviewed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    review_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    developer = relationship("Developer")
    project = relationship("Project")
    campaign_evidence = relationship("CampaignEvidence", back_populates="social_capture", cascade="all, delete-orphan")

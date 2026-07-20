from __future__ import annotations

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now


class CampaignEvidence(Base):
    __tablename__ = "campaign_evidence"
    __table_args__ = (
        Index("ix_campaign_evidence_social_capture_id", "social_capture_id"),
        Index("ix_campaign_evidence_developer_id", "developer_id"),
        Index("ix_campaign_evidence_project_id", "project_id"),
        Index("ix_campaign_evidence_platform", "platform"),
        Index("ix_campaign_evidence_campaign_type", "campaign_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    social_capture_id: Mapped[int] = mapped_column(ForeignKey("social_captures.id", ondelete="CASCADE"), nullable=False)
    developer_id: Mapped[int | None] = mapped_column(ForeignKey("developers.id", ondelete="SET NULL"))
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"))
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    campaign_type: Mapped[str] = mapped_column(String(80), nullable=False)
    advertiser_name: Mapped[str | None] = mapped_column(String(255))
    campaign_text: Mapped[str | None] = mapped_column(Text)
    call_to_action: Mapped[str | None] = mapped_column(String(255))
    destination_url: Mapped[str | None] = mapped_column(String(2048))
    visible_status: Mapped[str] = mapped_column(String(50), default="unknown")
    verification_status: Mapped[str] = mapped_column(String(80), default="unverified")
    first_seen_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    social_capture = relationship("SocialCapture", back_populates="campaign_evidence")
    developer = relationship("Developer")
    project = relationship("Project")


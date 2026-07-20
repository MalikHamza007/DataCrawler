from __future__ import annotations

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now


class Developer(Base):
    __tablename__ = "developers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str | None] = mapped_column(String(255), index=True)
    legal_name: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    classification: Mapped[str] = mapped_column(String(50), default="uncertain", index=True)
    verification_status: Mapped[str] = mapped_column(String(50), default="unverified", index=True)
    review_status: Mapped[str] = mapped_column(String(50), default="unreviewed", index=True)
    review_note: Mapped[str | None] = mapped_column(Text)
    last_reviewed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), index=True)
    outreach_status: Mapped[str] = mapped_column(String(50), default="not_contacted", index=True)
    last_outreach_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    next_follow_up_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), index=True)
    version_number: Mapped[int] = mapped_column(default=1, nullable=False)
    website_url: Mapped[str | None] = mapped_column(String(2048))
    office_address: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str] = mapped_column(String(100), default="Lahore", index=True)
    country: Mapped[str] = mapped_column(String(100), default="Pakistan")
    record_status: Mapped[str] = mapped_column(String(50), default="active", index=True)
    merged_into_developer_id: Mapped[int | None] = mapped_column(ForeignKey("developers.id", ondelete="SET NULL"), index=True)
    merged_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    projects = relationship("Project", back_populates="developer", passive_deletes=True)
    contacts = relationship("Contact", back_populates="developer", cascade="all, delete-orphan")
    social_profiles = relationship("SocialProfile", back_populates="developer", cascade="all, delete-orphan")
    evidence = relationship("SourceEvidence", back_populates="developer", cascade="all, delete-orphan")
    website_crawls = relationship("WebsiteCrawl", back_populates="developer")
    relationship_candidates = relationship("ProjectDeveloperRelationship", back_populates="developer")
    classification_assessments = relationship("ClassificationAssessment", back_populates="developer")

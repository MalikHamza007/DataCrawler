from __future__ import annotations

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (UniqueConstraint("google_place_id", name="uq_projects_google_place_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    developer_id: Mapped[int | None] = mapped_column(ForeignKey("developers.id", ondelete="SET NULL"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str | None] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    project_type: Mapped[str | None] = mapped_column(String(100), index=True)
    project_status: Mapped[str] = mapped_column(String(50), default="unknown", index=True)
    verification_status: Mapped[str] = mapped_column(String(50), default="unverified", index=True)
    review_status: Mapped[str] = mapped_column(String(50), default="unreviewed", index=True)
    review_note: Mapped[str | None] = mapped_column(Text)
    last_reviewed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), index=True)
    outreach_status: Mapped[str] = mapped_column(String(50), default="not_contacted", index=True)
    last_outreach_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    next_follow_up_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), index=True)
    version_number: Mapped[int] = mapped_column(default=1, nullable=False)
    address: Mapped[str | None] = mapped_column(Text)
    lahore_zone: Mapped[str | None] = mapped_column(String(150), index=True)
    city: Mapped[str] = mapped_column(String(100), default="Lahore")
    country: Mapped[str] = mapped_column(String(100), default="Pakistan")
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    google_place_id: Mapped[str | None] = mapped_column(String(255), index=True)
    google_maps_url: Mapped[str | None] = mapped_column(String(2048))
    official_website_url: Mapped[str | None] = mapped_column(String(2048))
    record_status: Mapped[str] = mapped_column(String(50), default="active", index=True)
    merged_into_project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), index=True)
    merged_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    developer = relationship("Developer", back_populates="projects")
    contacts = relationship("Contact", back_populates="project", cascade="all, delete-orphan")
    social_profiles = relationship("SocialProfile", back_populates="project", cascade="all, delete-orphan")
    evidence = relationship("SourceEvidence", back_populates="project", cascade="all, delete-orphan")
    website_crawls = relationship("WebsiteCrawl", back_populates="project")
    relationship_candidates = relationship("ProjectDeveloperRelationship", back_populates="project")
    classification_assessments = relationship("ClassificationAssessment", back_populates="project")

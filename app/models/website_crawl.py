from __future__ import annotations

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now


class WebsiteCrawl(Base):
    __tablename__ = "website_crawls"

    id: Mapped[int] = mapped_column(primary_key=True)
    collection_job_id: Mapped[int] = mapped_column(ForeignKey("collection_jobs.id", ondelete="CASCADE"), unique=True, index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), index=True)
    developer_id: Mapped[int | None] = mapped_column(ForeignKey("developers.id", ondelete="SET NULL"), index=True)
    seed_url: Mapped[str] = mapped_column(String(2048))
    canonical_seed_url: Mapped[str] = mapped_column(String(2048))
    registered_domain: Mapped[str] = mapped_column(String(255), index=True)
    crawl_mode: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(50), default="queued", index=True)
    robots_status: Mapped[str | None] = mapped_column(String(50))
    robots_url: Mapped[str | None] = mapped_column(String(2048))
    robots_fetched_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    robots_expires_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    pages_discovered: Mapped[int] = mapped_column(Integer, default=0)
    pages_queued: Mapped[int] = mapped_column(Integer, default=0)
    pages_fetched: Mapped[int] = mapped_column(Integer, default=0)
    pages_skipped: Mapped[int] = mapped_column(Integer, default=0)
    pages_failed: Mapped[int] = mapped_column(Integer, default=0)
    playwright_pages: Mapped[int] = mapped_column(Integer, default=0)
    projects_discovered: Mapped[int] = mapped_column(Integer, default=0)
    developers_discovered: Mapped[int] = mapped_column(Integer, default=0)
    contacts_discovered: Mapped[int] = mapped_column(Integer, default=0)
    social_profiles_discovered: Mapped[int] = mapped_column(Integer, default=0)
    warning_message: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    collection_job = relationship("CollectionJob", back_populates="website_crawl")
    project = relationship("Project", back_populates="website_crawls")
    developer = relationship("Developer", back_populates="website_crawls")
    pages = relationship("WebsitePage", back_populates="website_crawl", cascade="all, delete-orphan")


class WebsitePage(Base):
    __tablename__ = "website_pages"
    __table_args__ = (UniqueConstraint("website_crawl_id", "canonical_url", name="uq_website_pages_crawl_url"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    website_crawl_id: Mapped[int] = mapped_column(ForeignKey("website_crawls.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(String(2048))
    canonical_url: Mapped[str] = mapped_column(String(2048))
    parent_url: Mapped[str | None] = mapped_column(String(2048))
    depth: Mapped[int] = mapped_column(Integer)
    priority_score: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(50), default="discovered", index=True)
    http_status: Mapped[int | None] = mapped_column(Integer)
    content_type: Mapped[str | None] = mapped_column(String(255))
    fetch_method: Mapped[str | None] = mapped_column(String(20))
    title: Mapped[str | None] = mapped_column(String(500))
    meta_description: Mapped[str | None] = mapped_column(Text)
    canonical_tag: Mapped[str | None] = mapped_column(String(2048))
    etag: Mapped[str | None] = mapped_column(String(500))
    last_modified: Mapped[str | None] = mapped_column(String(500))
    content_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    text_length: Mapped[int] = mapped_column(Integer, default=0)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    fetched_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    error_type: Mapped[str | None] = mapped_column(String(255))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    website_crawl = relationship("WebsiteCrawl", back_populates="pages")

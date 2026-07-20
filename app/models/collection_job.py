from __future__ import annotations

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now


class CollectionJob(Base):
    __tablename__ = "collection_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_type: Mapped[str] = mapped_column(String(50), index=True)
    status: Mapped[str] = mapped_column(String(50), default="queued", index=True)
    city: Mapped[str] = mapped_column(String(100), default="Lahore")
    lahore_zone: Mapped[str | None] = mapped_column(String(150))
    search_config_json: Mapped[dict | None] = mapped_column(JSON)
    total_items: Mapped[int] = mapped_column(Integer, default=0)
    processed_items: Mapped[int] = mapped_column(Integer, default=0)
    created_items: Mapped[int] = mapped_column(Integer, default=0)
    updated_items: Mapped[int] = mapped_column(Integer, default=0)
    failed_items: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    worker_id: Mapped[str | None] = mapped_column(String(128), index=True)
    claimed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    heartbeat_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    lease_expires_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), index=True)
    cancel_requested_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    next_attempt_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), index=True)
    progress_phase: Mapped[str] = mapped_column(String(50), default="queued")
    progress_message: Mapped[str | None] = mapped_column(String(500))
    last_error_type: Mapped[str | None] = mapped_column(String(255))
    last_error_retryable: Mapped[bool | None] = mapped_column(Boolean)
    execution_summary_json: Mapped[dict | None] = mapped_column(JSON)
    started_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    logs = relationship("CollectionLog", back_populates="collection_job", cascade="all, delete-orphan")
    evidence = relationship("SourceEvidence", back_populates="collection_job", cascade="all, delete-orphan")
    website_crawl = relationship("WebsiteCrawl", back_populates="collection_job", uselist=False, cascade="all, delete-orphan")

    @property
    def progress_percent(self) -> int:
        if self.status == "completed":
            return 100
        if not self.total_items:
            return 0
        return max(0, min(100, int((self.processed_items / self.total_items) * 100)))

    @property
    def is_cancellable(self) -> bool:
        return self.status in {"queued", "running"}

    @property
    def is_retryable(self) -> bool:
        return self.status in {"failed", "cancelled"} and self.attempt_count < self.max_attempts

    @property
    def worker_active(self) -> bool:
        return bool(self.worker_id and self.status == "running")

    @property
    def website_crawl_id(self) -> int | None:
        return self.website_crawl.id if self.website_crawl else None


class CollectionLog(Base):
    __tablename__ = "collection_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    collection_job_id: Mapped[int] = mapped_column(ForeignKey("collection_jobs.id", ondelete="CASCADE"), index=True)
    level: Mapped[str] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(Text)
    context_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    collection_job = relationship("CollectionJob", back_populates="logs")

from __future__ import annotations

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now


class ExportArtifact(Base):
    __tablename__ = "export_artifacts"
    __table_args__ = (
        Index("ix_export_artifacts_collection_job_id", "collection_job_id"),
        Index("ix_export_artifacts_format", "format"),
        Index("ix_export_artifacts_scope", "scope"),
        Index("ix_export_artifacts_status", "status"),
        Index("ix_export_artifacts_created_at", "created_at"),
        Index("ix_export_artifacts_generated_at", "generated_at"),
        Index("ix_export_artifacts_expires_at", "expires_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    collection_job_id: Mapped[int] = mapped_column(ForeignKey("collection_jobs.id", ondelete="CASCADE"), nullable=False)
    format: Mapped[str] = mapped_column(String(20), nullable=False)
    scope: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="queued", nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    internal_filename: Mapped[str | None] = mapped_column(String(255), unique=True)
    media_type: Mapped[str] = mapped_column(String(255), nullable=False)
    filter_snapshot_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    options_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    summary_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    row_count: Mapped[int | None] = mapped_column(Integer)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer)
    sha256: Mapped[str | None] = mapped_column(String(64))
    generated_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    download_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_downloaded_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    collection_job = relationship("CollectionJob")

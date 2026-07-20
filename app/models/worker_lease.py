from __future__ import annotations

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now


class WorkerLease(Base):
    __tablename__ = "worker_leases"
    __table_args__ = (UniqueConstraint("lease_name", name="uq_worker_leases_lease_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    lease_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    owner_id: Mapped[str | None] = mapped_column(String(255), index=True)
    hostname: Mapped[str | None] = mapped_column(String(255))
    process_id: Mapped[int | None] = mapped_column(Integer)
    started_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    heartbeat_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

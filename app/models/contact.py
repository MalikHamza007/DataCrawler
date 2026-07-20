from __future__ import annotations

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now


class Contact(Base):
    __tablename__ = "contacts"
    __table_args__ = (
        CheckConstraint(
            "(developer_id IS NOT NULL AND project_id IS NULL) OR (developer_id IS NULL AND project_id IS NOT NULL)",
            name="ck_contacts_exactly_one_owner",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    developer_id: Mapped[int | None] = mapped_column(ForeignKey("developers.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    contact_type: Mapped[str] = mapped_column(String(50), index=True)
    label: Mapped[str | None] = mapped_column(String(255))
    value: Mapped[str] = mapped_column(String(2048))
    normalized_value: Mapped[str | None] = mapped_column(String(2048), index=True)
    person_name: Mapped[str | None] = mapped_column(String(255))
    designation: Mapped[str | None] = mapped_column(String(255))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    is_public_business_contact: Mapped[bool] = mapped_column(Boolean, default=True)
    verification_status: Mapped[str] = mapped_column(String(50), default="unverified")
    source_url: Mapped[str | None] = mapped_column(String(2048))
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    developer = relationship("Developer", back_populates="contacts")
    project = relationship("Project", back_populates="contacts")

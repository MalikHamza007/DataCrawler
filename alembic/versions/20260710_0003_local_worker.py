"""add local worker fields

Revision ID: 20260710_0003
Revises: 20260710_0002
Create Date: 2026-07-10
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260710_0003"
down_revision = "20260710_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("collection_jobs") as batch:
        batch.add_column(sa.Column("worker_id", sa.String(length=128), nullable=True))
        batch.add_column(sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("cancel_requested_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"))
        batch.add_column(sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("progress_phase", sa.String(length=50), nullable=False, server_default="queued"))
        batch.add_column(sa.Column("progress_message", sa.String(length=500), nullable=True))
        batch.add_column(sa.Column("last_error_type", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("last_error_retryable", sa.Boolean(), nullable=True))
        batch.add_column(sa.Column("execution_summary_json", sa.JSON(), nullable=True))
    op.create_index("ix_collection_jobs_worker_id", "collection_jobs", ["worker_id"])
    op.create_index("ix_collection_jobs_lease_expires_at", "collection_jobs", ["lease_expires_at"])
    op.create_index("ix_collection_jobs_next_attempt_at", "collection_jobs", ["next_attempt_at"])
    op.create_index("ix_collection_jobs_status_next_attempt_created", "collection_jobs", ["status", "next_attempt_at", "created_at"])

    op.create_table(
        "worker_leases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lease_name", sa.String(length=128), nullable=False),
        sa.Column("owner_id", sa.String(length=255), nullable=True),
        sa.Column("hostname", sa.String(length=255), nullable=True),
        sa.Column("process_id", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("lease_name", name="uq_worker_leases_lease_name"),
    )
    op.create_index("ix_worker_leases_lease_name", "worker_leases", ["lease_name"])
    op.create_index("ix_worker_leases_owner_id", "worker_leases", ["owner_id"])
    op.create_index("ix_worker_leases_expires_at", "worker_leases", ["expires_at"])


def downgrade() -> None:
    op.drop_table("worker_leases")
    op.drop_index("ix_collection_jobs_status_next_attempt_created", table_name="collection_jobs")
    op.drop_index("ix_collection_jobs_next_attempt_at", table_name="collection_jobs")
    op.drop_index("ix_collection_jobs_lease_expires_at", table_name="collection_jobs")
    op.drop_index("ix_collection_jobs_worker_id", table_name="collection_jobs")
    with op.batch_alter_table("collection_jobs") as batch:
        batch.drop_column("execution_summary_json")
        batch.drop_column("last_error_retryable")
        batch.drop_column("last_error_type")
        batch.drop_column("progress_message")
        batch.drop_column("progress_phase")
        batch.drop_column("next_attempt_at")
        batch.drop_column("max_attempts")
        batch.drop_column("attempt_count")
        batch.drop_column("cancel_requested_at")
        batch.drop_column("lease_expires_at")
        batch.drop_column("heartbeat_at")
        batch.drop_column("claimed_at")
        batch.drop_column("worker_id")

"""add export artifacts

Revision ID: 20260713_0008
Revises: 20260713_0007
Create Date: 2026-07-13 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260713_0008"
down_revision = "20260713_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "export_artifacts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("collection_job_id", sa.Integer(), nullable=False),
        sa.Column("format", sa.String(length=20), nullable=False),
        sa.Column("scope", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("internal_filename", sa.String(length=255), nullable=True),
        sa.Column("media_type", sa.String(length=255), nullable=False),
        sa.Column("filter_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("options_json", sa.JSON(), nullable=False),
        sa.Column("summary_json", sa.JSON(), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("download_count", sa.Integer(), nullable=False),
        sa.Column("last_downloaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["collection_job_id"], ["collection_jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("internal_filename"),
    )
    op.create_index("ix_export_artifacts_collection_job_id", "export_artifacts", ["collection_job_id"])
    op.create_index("ix_export_artifacts_format", "export_artifacts", ["format"])
    op.create_index("ix_export_artifacts_scope", "export_artifacts", ["scope"])
    op.create_index("ix_export_artifacts_status", "export_artifacts", ["status"])
    op.create_index("ix_export_artifacts_created_at", "export_artifacts", ["created_at"])
    op.create_index("ix_export_artifacts_generated_at", "export_artifacts", ["generated_at"])
    op.create_index("ix_export_artifacts_expires_at", "export_artifacts", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_export_artifacts_expires_at", table_name="export_artifacts")
    op.drop_index("ix_export_artifacts_generated_at", table_name="export_artifacts")
    op.drop_index("ix_export_artifacts_created_at", table_name="export_artifacts")
    op.drop_index("ix_export_artifacts_status", table_name="export_artifacts")
    op.drop_index("ix_export_artifacts_scope", table_name="export_artifacts")
    op.drop_index("ix_export_artifacts_format", table_name="export_artifacts")
    op.drop_index("ix_export_artifacts_collection_job_id", table_name="export_artifacts")
    op.drop_table("export_artifacts")

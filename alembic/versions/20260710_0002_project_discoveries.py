"""add project discoveries

Revision ID: 20260710_0002
Revises: 20260710_0001
Create Date: 2026-07-10
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260710_0002"
down_revision = "20260710_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_discoveries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("collection_job_id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("source_method", sa.String(length=50), nullable=False),
        sa.Column("source_query", sa.String(length=500), nullable=True),
        sa.Column("source_cell_id", sa.String(length=100), nullable=True),
        sa.Column("google_primary_type", sa.String(length=100), nullable=True),
        sa.Column("google_types_json", sa.JSON(), nullable=True),
        sa.Column("google_business_status", sa.String(length=100), nullable=True),
        sa.Column("encounter_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("first_discovered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_discovered_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["collection_job_id"], ["collection_jobs.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_project_discoveries_project_id", "project_discoveries", ["project_id"])
    op.create_index("ix_project_discoveries_collection_job_id", "project_discoveries", ["collection_job_id"])
    op.create_index("ix_project_discoveries_source", "project_discoveries", ["source"])
    op.create_index("ix_project_discoveries_source_method", "project_discoveries", ["source_method"])
    op.create_index("ix_project_discoveries_source_cell_id", "project_discoveries", ["source_cell_id"])


def downgrade() -> None:
    op.drop_table("project_discoveries")

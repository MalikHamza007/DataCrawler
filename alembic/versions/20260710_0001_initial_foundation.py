"""initial foundation

Revision ID: 20260710_0001
Revises:
Create Date: 2026-07-10
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260710_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "developers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=True),
        sa.Column("legal_name", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("classification", sa.String(length=50), nullable=False, server_default="uncertain"),
        sa.Column("verification_status", sa.String(length=50), nullable=False, server_default="unverified"),
        sa.Column("website_url", sa.String(length=2048), nullable=True),
        sa.Column("office_address", sa.Text(), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=False, server_default="Lahore"),
        sa.Column("country", sa.String(length=100), nullable=False, server_default="Pakistan"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_developers_normalized_name", "developers", ["normalized_name"])
    op.create_index("ix_developers_classification", "developers", ["classification"])
    op.create_index("ix_developers_verification_status", "developers", ["verification_status"])
    op.create_index("ix_developers_city", "developers", ["city"])

    op.create_table(
        "collection_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="queued"),
        sa.Column("city", sa.String(length=100), nullable=False, server_default="Lahore"),
        sa.Column("lahore_zone", sa.String(length=150), nullable=True),
        sa.Column("search_config_json", sa.JSON(), nullable=True),
        sa.Column("total_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processed_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_collection_jobs_status", "collection_jobs", ["status"])
    op.create_index("ix_collection_jobs_job_type", "collection_jobs", ["job_type"])
    op.create_index("ix_collection_jobs_created_at", "collection_jobs", ["created_at"])

    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("developer_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("project_type", sa.String(length=100), nullable=True),
        sa.Column("project_status", sa.String(length=50), nullable=False, server_default="unknown"),
        sa.Column("verification_status", sa.String(length=50), nullable=False, server_default="unverified"),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("lahore_zone", sa.String(length=150), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=False, server_default="Lahore"),
        sa.Column("country", sa.String(length=100), nullable=False, server_default="Pakistan"),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("google_place_id", sa.String(length=255), nullable=True),
        sa.Column("google_maps_url", sa.String(length=2048), nullable=True),
        sa.Column("official_website_url", sa.String(length=2048), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["developer_id"], ["developers.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("google_place_id", name="uq_projects_google_place_id"),
    )
    op.create_index("ix_projects_normalized_name", "projects", ["normalized_name"])
    op.create_index("ix_projects_developer_id", "projects", ["developer_id"])
    op.create_index("ix_projects_lahore_zone", "projects", ["lahore_zone"])
    op.create_index("ix_projects_project_type", "projects", ["project_type"])
    op.create_index("ix_projects_project_status", "projects", ["project_status"])
    op.create_index("ix_projects_verification_status", "projects", ["verification_status"])
    op.create_index("ix_projects_google_place_id", "projects", ["google_place_id"])

    op.create_table(
        "collection_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("collection_job_id", sa.Integer(), nullable=False),
        sa.Column("level", sa.String(length=20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("context_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["collection_job_id"], ["collection_jobs.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_collection_logs_collection_job_id", "collection_logs", ["collection_job_id"])

    owner_check = "(developer_id IS NOT NULL AND project_id IS NULL) OR (developer_id IS NULL AND project_id IS NOT NULL)"
    op.create_table(
        "contacts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("developer_id", sa.Integer(), nullable=True),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("contact_type", sa.String(length=50), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("value", sa.String(length=2048), nullable=False),
        sa.Column("normalized_value", sa.String(length=2048), nullable=True),
        sa.Column("person_name", sa.String(length=255), nullable=True),
        sa.Column("designation", sa.String(length=255), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_public_business_contact", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("verification_status", sa.String(length=50), nullable=False, server_default="unverified"),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(owner_check, name="ck_contacts_exactly_one_owner"),
        sa.ForeignKeyConstraint(["developer_id"], ["developers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_contacts_developer_id", "contacts", ["developer_id"])
    op.create_index("ix_contacts_project_id", "contacts", ["project_id"])
    op.create_index("ix_contacts_contact_type", "contacts", ["contact_type"])
    op.create_index("ix_contacts_normalized_value", "contacts", ["normalized_value"])

    op.create_table(
        "social_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("developer_id", sa.Integer(), nullable=True),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("profile_name", sa.String(length=255), nullable=True),
        sa.Column("profile_url", sa.String(length=2048), nullable=False),
        sa.Column("normalized_url", sa.String(length=2048), nullable=True),
        sa.Column("is_official", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("verification_status", sa.String(length=50), nullable=False, server_default="unverified"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(owner_check, name="ck_social_profiles_exactly_one_owner"),
        sa.ForeignKeyConstraint(["developer_id"], ["developers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_social_profiles_developer_id", "social_profiles", ["developer_id"])
    op.create_index("ix_social_profiles_project_id", "social_profiles", ["project_id"])
    op.create_index("ix_social_profiles_platform", "social_profiles", ["platform"])
    op.create_index("ix_social_profiles_normalized_url", "social_profiles", ["normalized_url"])

    op.create_table(
        "source_evidence",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("developer_id", sa.Integer(), nullable=True),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("collection_job_id", sa.Integer(), nullable=True),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=False),
        sa.Column("source_title", sa.String(length=255), nullable=True),
        sa.Column("captured_text", sa.Text(), nullable=True),
        sa.Column("field_name", sa.String(length=255), nullable=True),
        sa.Column("extracted_value", sa.String(length=2048), nullable=True),
        sa.Column("verification_status", sa.String(length=50), nullable=False, server_default="unverified"),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "developer_id IS NOT NULL OR project_id IS NOT NULL OR collection_job_id IS NOT NULL",
            name="ck_source_evidence_at_least_one_owner",
        ),
        sa.ForeignKeyConstraint(["developer_id"], ["developers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["collection_job_id"], ["collection_jobs.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_source_evidence_developer_id", "source_evidence", ["developer_id"])
    op.create_index("ix_source_evidence_project_id", "source_evidence", ["project_id"])
    op.create_index("ix_source_evidence_collection_job_id", "source_evidence", ["collection_job_id"])
    op.create_index("ix_source_evidence_source_type", "source_evidence", ["source_type"])
    op.create_index("ix_source_evidence_verification_status", "source_evidence", ["verification_status"])


def downgrade() -> None:
    op.drop_table("source_evidence")
    op.drop_table("social_profiles")
    op.drop_table("contacts")
    op.drop_table("collection_logs")
    op.drop_table("projects")
    op.drop_table("collection_jobs")
    op.drop_table("developers")

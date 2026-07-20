"""add social capture extension tables

Revision ID: 20260713_0006
Revises: 20260711_0005
Create Date: 2026-07-13 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260713_0006"
down_revision = "20260711_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "social_captures",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("page_kind", sa.String(length=80), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=False),
        sa.Column("canonical_url", sa.String(length=2048), nullable=True),
        sa.Column("page_title", sa.String(length=255), nullable=True),
        sa.Column("profile_name", sa.String(length=255), nullable=True),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("visible_text_excerpt", sa.Text(), nullable=True),
        sa.Column("about_text", sa.Text(), nullable=True),
        sa.Column("capture_payload_json", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("extractor_version", sa.String(length=80), nullable=False),
        sa.Column("capture_version", sa.String(length=20), nullable=False),
        sa.Column("extension_version", sa.String(length=50), nullable=True),
        sa.Column("developer_id", sa.Integer(), nullable=True),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("review_status", sa.String(length=50), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["developer_id"], ["developers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_social_captures_platform", "social_captures", ["platform"])
    op.create_index("ix_social_captures_page_kind", "social_captures", ["page_kind"])
    op.create_index("ix_social_captures_developer_id", "social_captures", ["developer_id"])
    op.create_index("ix_social_captures_project_id", "social_captures", ["project_id"])
    op.create_index("ix_social_captures_review_status", "social_captures", ["review_status"])
    op.create_index("ix_social_captures_captured_at", "social_captures", ["captured_at"])
    op.create_index("ix_social_captures_content_hash", "social_captures", ["content_hash"])
    op.create_index("ix_social_captures_canonical_url", "social_captures", ["canonical_url"])

    op.create_table(
        "campaign_evidence",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("social_capture_id", sa.Integer(), nullable=False),
        sa.Column("developer_id", sa.Integer(), nullable=True),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("campaign_type", sa.String(length=80), nullable=False),
        sa.Column("advertiser_name", sa.String(length=255), nullable=True),
        sa.Column("campaign_text", sa.Text(), nullable=True),
        sa.Column("call_to_action", sa.String(length=255), nullable=True),
        sa.Column("destination_url", sa.String(length=2048), nullable=True),
        sa.Column("visible_status", sa.String(length=50), nullable=True),
        sa.Column("verification_status", sa.String(length=80), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["developer_id"], ["developers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["social_capture_id"], ["social_captures.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_campaign_evidence_social_capture_id", "campaign_evidence", ["social_capture_id"])
    op.create_index("ix_campaign_evidence_developer_id", "campaign_evidence", ["developer_id"])
    op.create_index("ix_campaign_evidence_project_id", "campaign_evidence", ["project_id"])
    op.create_index("ix_campaign_evidence_platform", "campaign_evidence", ["platform"])
    op.create_index("ix_campaign_evidence_campaign_type", "campaign_evidence", ["campaign_type"])


def downgrade() -> None:
    op.drop_index("ix_campaign_evidence_campaign_type", table_name="campaign_evidence")
    op.drop_index("ix_campaign_evidence_platform", table_name="campaign_evidence")
    op.drop_index("ix_campaign_evidence_project_id", table_name="campaign_evidence")
    op.drop_index("ix_campaign_evidence_developer_id", table_name="campaign_evidence")
    op.drop_index("ix_campaign_evidence_social_capture_id", table_name="campaign_evidence")
    op.drop_table("campaign_evidence")
    op.drop_index("ix_social_captures_canonical_url", table_name="social_captures")
    op.drop_index("ix_social_captures_content_hash", table_name="social_captures")
    op.drop_index("ix_social_captures_captured_at", table_name="social_captures")
    op.drop_index("ix_social_captures_review_status", table_name="social_captures")
    op.drop_index("ix_social_captures_project_id", table_name="social_captures")
    op.drop_index("ix_social_captures_developer_id", table_name="social_captures")
    op.drop_index("ix_social_captures_page_kind", table_name="social_captures")
    op.drop_index("ix_social_captures_platform", table_name="social_captures")
    op.drop_table("social_captures")


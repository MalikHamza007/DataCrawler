"""add dashboard review and outreach workflow

Revision ID: 20260713_0007
Revises: 20260713_0006
Create Date: 2026-07-13 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260713_0007"
down_revision = "20260713_0006"
branch_labels = None
depends_on = None


def _add_record_columns(table: str) -> None:
    with op.batch_alter_table(table) as batch:
        batch.add_column(sa.Column("review_status", sa.String(length=50), nullable=False, server_default="unreviewed"))
        batch.add_column(sa.Column("review_note", sa.Text(), nullable=True))
        batch.add_column(sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("outreach_status", sa.String(length=50), nullable=False, server_default="not_contacted"))
        batch.add_column(sa.Column("last_outreach_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("next_follow_up_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"))


def _drop_record_columns(table: str) -> None:
    with op.batch_alter_table(table) as batch:
        batch.drop_column("version_number")
        batch.drop_column("next_follow_up_at")
        batch.drop_column("last_outreach_at")
        batch.drop_column("outreach_status")
        batch.drop_column("last_reviewed_at")
        batch.drop_column("review_note")
        batch.drop_column("review_status")


def upgrade() -> None:
    _add_record_columns("developers")
    _add_record_columns("projects")
    for table in ("developers", "projects"):
        op.create_index(f"ix_{table}_review_status", table, ["review_status"])
        op.create_index(f"ix_{table}_outreach_status", table, ["outreach_status"])
        op.create_index(f"ix_{table}_next_follow_up_at", table, ["next_follow_up_at"])
        op.create_index(f"ix_{table}_last_reviewed_at", table, ["last_reviewed_at"])

    op.create_table(
        "outreach_activities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("developer_id", sa.Integer(), nullable=True),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("activity_type", sa.String(length=50), nullable=False),
        sa.Column("channel", sa.String(length=50), nullable=False),
        sa.Column("direction", sa.String(length=50), nullable=False),
        sa.Column("status_after", sa.String(length=50), nullable=True),
        sa.Column("contact_value", sa.String(length=2048), nullable=True),
        sa.Column("contact_person", sa.String(length=255), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("follow_up_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("(developer_id IS NOT NULL AND project_id IS NULL) OR (developer_id IS NULL AND project_id IS NOT NULL)", name="ck_outreach_activities_exactly_one_owner"),
        sa.ForeignKeyConstraint(["developer_id"], ["developers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("developer_id", "project_id", "activity_type", "channel", "occurred_at", "follow_up_at"):
        op.create_index(f"ix_outreach_activities_{column}", "outreach_activities", [column])

    op.create_table(
        "review_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("developer_id", sa.Integer(), nullable=True),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("social_capture_id", sa.Integer(), nullable=True),
        sa.Column("classification_assessment_id", sa.Integer(), nullable=True),
        sa.Column("relationship_id", sa.Integer(), nullable=True),
        sa.Column("duplicate_candidate_id", sa.Integer(), nullable=True),
        sa.Column("action_type", sa.String(length=80), nullable=False),
        sa.Column("before_json", sa.Text(), nullable=True),
        sa.Column("after_json", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("operator_label", sa.String(length=255), nullable=False, server_default="Local Operator"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("developer_id IS NOT NULL OR project_id IS NOT NULL OR social_capture_id IS NOT NULL OR classification_assessment_id IS NOT NULL OR relationship_id IS NOT NULL OR duplicate_candidate_id IS NOT NULL", name="ck_review_events_at_least_one_entity"),
        sa.ForeignKeyConstraint(["classification_assessment_id"], ["classification_assessments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["developer_id"], ["developers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["duplicate_candidate_id"], ["duplicate_candidates.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["relationship_id"], ["project_developer_relationships.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["social_capture_id"], ["social_captures.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("developer_id", "project_id", "action_type", "created_at"):
        op.create_index(f"ix_review_events_{column}", "review_events", [column])

    op.create_table(
        "field_verifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("developer_id", sa.Integer(), nullable=True),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("field_name", sa.String(length=100), nullable=False),
        sa.Column("verified_value", sa.String(length=2048), nullable=False),
        sa.Column("verification_status", sa.String(length=50), nullable=False),
        sa.Column("source_evidence_id", sa.Integer(), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("(developer_id IS NOT NULL AND project_id IS NULL) OR (developer_id IS NULL AND project_id IS NOT NULL)", name="ck_field_verifications_exactly_one_owner"),
        sa.ForeignKeyConstraint(["developer_id"], ["developers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_evidence_id"], ["source_evidence.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("developer_id", "project_id", "field_name", "verification_status"):
        op.create_index(f"ix_field_verifications_{column}", "field_verifications", [column])


def downgrade() -> None:
    for column in ("developer_id", "project_id", "field_name", "verification_status"):
        op.drop_index(f"ix_field_verifications_{column}", table_name="field_verifications")
    op.drop_table("field_verifications")
    for column in ("developer_id", "project_id", "action_type", "created_at"):
        op.drop_index(f"ix_review_events_{column}", table_name="review_events")
    op.drop_table("review_events")
    for column in ("developer_id", "project_id", "activity_type", "channel", "occurred_at", "follow_up_at"):
        op.drop_index(f"ix_outreach_activities_{column}", table_name="outreach_activities")
    op.drop_table("outreach_activities")
    for table in ("developers", "projects"):
        op.drop_index(f"ix_{table}_last_reviewed_at", table_name=table)
        op.drop_index(f"ix_{table}_next_follow_up_at", table_name=table)
        op.drop_index(f"ix_{table}_outreach_status", table_name=table)
        op.drop_index(f"ix_{table}_review_status", table_name=table)
    _drop_record_columns("projects")
    _drop_record_columns("developers")


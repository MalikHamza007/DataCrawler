"""add intelligence review

Revision ID: 20260711_0005
Revises: 20260711_0004
"""
from alembic import op
import sqlalchemy as sa

revision = "20260711_0005"
down_revision = "20260711_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("developers") as batch:
        batch.add_column(sa.Column("record_status", sa.String(50), nullable=False, server_default="active"))
        batch.add_column(sa.Column("merged_into_developer_id", sa.Integer()))
        batch.add_column(sa.Column("merged_at", sa.DateTime(timezone=True)))
        batch.create_foreign_key("fk_developers_merged_into", "developers", ["merged_into_developer_id"], ["id"], ondelete="SET NULL")
        batch.create_index("ix_developers_record_status", ["record_status"])
        batch.create_index("ix_developers_merged_into_developer_id", ["merged_into_developer_id"])
    with op.batch_alter_table("projects") as batch:
        batch.add_column(sa.Column("record_status", sa.String(50), nullable=False, server_default="active"))
        batch.add_column(sa.Column("merged_into_project_id", sa.Integer()))
        batch.add_column(sa.Column("merged_at", sa.DateTime(timezone=True)))
        batch.create_foreign_key("fk_projects_merged_into", "projects", ["merged_into_project_id"], ["id"], ondelete="SET NULL")
        batch.create_index("ix_projects_record_status", ["record_status"])
        batch.create_index("ix_projects_merged_into_project_id", ["merged_into_project_id"])
    with op.batch_alter_table("project_developer_relationships") as batch:
        batch.add_column(sa.Column("system_score", sa.Integer()))
        batch.add_column(sa.Column("confidence_level", sa.String(50)))
        batch.add_column(sa.Column("signals_json", sa.JSON()))
        batch.add_column(sa.Column("explanation", sa.Text()))
        batch.add_column(sa.Column("rule_version", sa.String(50)))
        batch.add_column(sa.Column("evaluated_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("reviewed_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("review_note", sa.Text()))
        batch.create_index("ix_relationship_confidence", ["confidence_level"])
        batch.create_index("ix_relationship_rule_version", ["rule_version"])
    op.create_table(
        "classification_assessments",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("developer_id", sa.Integer()), sa.Column("project_id", sa.Integer()),
        sa.Column("entity_type", sa.String(50), nullable=False), sa.Column("suggested_classification", sa.String(50), nullable=False),
        sa.Column("system_score", sa.Integer(), nullable=False), sa.Column("confidence_level", sa.String(50), nullable=False),
        sa.Column("signals_json", sa.JSON(), nullable=False), sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("rule_version", sa.String(50), nullable=False), sa.Column("assessment_status", sa.String(50), nullable=False, server_default="pending_review"),
        sa.Column("manual_classification", sa.String(50)), sa.Column("manual_note", sa.Text()), sa.Column("manually_reviewed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["developer_id"], ["developers.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.CheckConstraint("(developer_id IS NOT NULL AND project_id IS NULL) OR (developer_id IS NULL AND project_id IS NOT NULL)", name="ck_assessment_one_owner"),
        sa.UniqueConstraint("entity_type", "developer_id", "project_id", "rule_version", name="uq_assessment_entity_rule"),
    )
    for name in ("developer_id", "project_id", "entity_type", "suggested_classification", "system_score", "confidence_level", "assessment_status", "rule_version", "created_at"):
        op.create_index(f"ix_classification_assessments_{name}", "classification_assessments", [name])
    op.create_table(
        "merge_operations",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("survivor_developer_id", sa.Integer()), sa.Column("absorbed_developer_id", sa.Integer()), sa.Column("survivor_project_id", sa.Integer()), sa.Column("absorbed_project_id", sa.Integer()),
        sa.Column("duplicate_candidate_id", sa.Integer()), sa.Column("preview_json", sa.JSON(), nullable=False), sa.Column("actions_json", sa.JSON()), sa.Column("conflicts_json", sa.JSON()),
        sa.Column("operator_note", sa.Text()), sa.Column("status", sa.String(50), nullable=False, server_default="previewed"), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["survivor_developer_id"], ["developers.id"], ondelete="SET NULL"), sa.ForeignKeyConstraint(["absorbed_developer_id"], ["developers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["survivor_project_id"], ["projects.id"], ondelete="SET NULL"), sa.ForeignKeyConstraint(["absorbed_project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.CheckConstraint("(entity_type = 'developer' AND survivor_developer_id IS NOT NULL AND absorbed_developer_id IS NOT NULL AND survivor_project_id IS NULL AND absorbed_project_id IS NULL AND survivor_developer_id <> absorbed_developer_id) OR (entity_type = 'project' AND survivor_project_id IS NOT NULL AND absorbed_project_id IS NOT NULL AND survivor_developer_id IS NULL AND absorbed_developer_id IS NULL AND survivor_project_id <> absorbed_project_id)", name="ck_merge_valid_pair"),
    )
    op.create_index("ix_merge_operations_entity_type", "merge_operations", ["entity_type"]); op.create_index("ix_merge_operations_status", "merge_operations", ["status"]); op.create_index("ix_merge_operations_duplicate_candidate_id", "merge_operations", ["duplicate_candidate_id"])
    op.create_table(
        "duplicate_candidates",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("left_developer_id", sa.Integer()), sa.Column("right_developer_id", sa.Integer()), sa.Column("left_project_id", sa.Integer()), sa.Column("right_project_id", sa.Integer()),
        sa.Column("duplicate_score", sa.Integer(), nullable=False), sa.Column("confidence_level", sa.String(50), nullable=False), sa.Column("signals_json", sa.JSON(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False), sa.Column("rule_version", sa.String(50), nullable=False), sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("review_note", sa.Text()), sa.Column("reviewed_at", sa.DateTime(timezone=True)), sa.Column("merge_operation_id", sa.Integer()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["left_developer_id"], ["developers.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["right_developer_id"], ["developers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["left_project_id"], ["projects.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["right_project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.CheckConstraint("(entity_type = 'developer' AND left_developer_id IS NOT NULL AND right_developer_id IS NOT NULL AND left_project_id IS NULL AND right_project_id IS NULL AND left_developer_id < right_developer_id) OR (entity_type = 'project' AND left_project_id IS NOT NULL AND right_project_id IS NOT NULL AND left_developer_id IS NULL AND right_developer_id IS NULL AND left_project_id < right_project_id)", name="ck_duplicate_valid_ordered_pair"),
        sa.UniqueConstraint("entity_type", "left_developer_id", "right_developer_id", "left_project_id", "right_project_id", "rule_version", name="uq_duplicate_pair_rule"),
    )
    for name in ("entity_type", "status", "duplicate_score", "confidence_level", "rule_version", "created_at"):
        op.create_index(f"ix_duplicate_candidates_{name}", "duplicate_candidates", [name])


def downgrade() -> None:
    op.drop_table("duplicate_candidates"); op.drop_table("merge_operations"); op.drop_table("classification_assessments")
    with op.batch_alter_table("project_developer_relationships") as batch:
        batch.drop_index("ix_relationship_rule_version"); batch.drop_index("ix_relationship_confidence")
        for column in ("review_note", "reviewed_at", "evaluated_at", "rule_version", "explanation", "signals_json", "confidence_level", "system_score"): batch.drop_column(column)
    with op.batch_alter_table("projects") as batch:
        batch.drop_index("ix_projects_merged_into_project_id"); batch.drop_index("ix_projects_record_status"); batch.drop_constraint("fk_projects_merged_into", type_="foreignkey")
        batch.drop_column("merged_at"); batch.drop_column("merged_into_project_id"); batch.drop_column("record_status")
    with op.batch_alter_table("developers") as batch:
        batch.drop_index("ix_developers_merged_into_developer_id"); batch.drop_index("ix_developers_record_status"); batch.drop_constraint("fk_developers_merged_into", type_="foreignkey")
        batch.drop_column("merged_at"); batch.drop_column("merged_into_developer_id"); batch.drop_column("record_status")

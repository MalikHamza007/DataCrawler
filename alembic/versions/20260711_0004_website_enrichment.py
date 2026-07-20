"""add website enrichment

Revision ID: 20260711_0004
Revises: 20260710_0003
Create Date: 2026-07-11
"""
from alembic import op
import sqlalchemy as sa

revision = "20260711_0004"
down_revision = "20260710_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "website_crawls",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("collection_job_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer()),
        sa.Column("developer_id", sa.Integer()),
        sa.Column("seed_url", sa.String(2048), nullable=False),
        sa.Column("canonical_seed_url", sa.String(2048), nullable=False),
        sa.Column("registered_domain", sa.String(255), nullable=False),
        sa.Column("crawl_mode", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="queued"),
        sa.Column("robots_status", sa.String(50)), sa.Column("robots_url", sa.String(2048)),
        sa.Column("robots_fetched_at", sa.DateTime(timezone=True)), sa.Column("robots_expires_at", sa.DateTime(timezone=True)),
        sa.Column("started_at", sa.DateTime(timezone=True)), sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("pages_discovered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pages_queued", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pages_fetched", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pages_skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pages_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("playwright_pages", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("projects_discovered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("developers_discovered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("contacts_discovered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("social_profiles_discovered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("warning_message", sa.Text()), sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["collection_job_id"], ["collection_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["developer_id"], ["developers.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("collection_job_id"),
    )
    for name, cols in (("collection_job_id", ["collection_job_id"]), ("project_id", ["project_id"]), ("developer_id", ["developer_id"]), ("registered_domain", ["registered_domain"]), ("status", ["status"]), ("created_at", ["created_at"])):
        op.create_index(f"ix_website_crawls_{name}", "website_crawls", cols)
    op.create_table(
        "website_pages",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("website_crawl_id", sa.Integer(), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False), sa.Column("canonical_url", sa.String(2048), nullable=False),
        sa.Column("parent_url", sa.String(2048)), sa.Column("depth", sa.Integer(), nullable=False),
        sa.Column("priority_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(50), nullable=False, server_default="discovered"), sa.Column("http_status", sa.Integer()),
        sa.Column("content_type", sa.String(255)), sa.Column("fetch_method", sa.String(20)), sa.Column("title", sa.String(500)),
        sa.Column("meta_description", sa.Text()), sa.Column("canonical_tag", sa.String(2048)), sa.Column("etag", sa.String(500)),
        sa.Column("last_modified", sa.String(500)), sa.Column("content_hash", sa.String(64)),
        sa.Column("text_length", sa.Integer(), nullable=False, server_default="0"), sa.Column("word_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fetched_at", sa.DateTime(timezone=True)), sa.Column("error_type", sa.String(255)), sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["website_crawl_id"], ["website_crawls.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("website_crawl_id", "canonical_url", name="uq_website_pages_crawl_url"),
    )
    op.create_index("ix_website_pages_website_crawl_id", "website_pages", ["website_crawl_id"])
    op.create_index("ix_website_pages_status", "website_pages", ["status"])
    op.create_index("ix_website_pages_content_hash", "website_pages", ["content_hash"])
    op.create_table(
        "project_developer_relationships",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("developer_id", sa.Integer(), nullable=False), sa.Column("relationship_type", sa.String(50), nullable=False, server_default="unknown"),
        sa.Column("status", sa.String(50), nullable=False, server_default="candidate"), sa.Column("source_evidence_id", sa.Integer()),
        sa.Column("source_url", sa.String(2048), nullable=False), sa.Column("evidence_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["developer_id"], ["developers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_evidence_id"], ["source_evidence.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("project_id", "developer_id", "relationship_type", "source_url", name="uq_project_developer_candidate"),
    )
    for name in ("project_id", "developer_id", "source_evidence_id", "status"):
        op.create_index(f"ix_project_developer_relationships_{name}", "project_developer_relationships", [name])


def downgrade() -> None:
    op.drop_table("project_developer_relationships")
    op.drop_table("website_pages")
    op.drop_table("website_crawls")

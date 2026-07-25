"""Create initial Abdul Core schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-07-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_initial_schema"
down_revision = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Create tables, indexes, and seed known sources."""

    op.create_table(
        "sources",
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(op.f("ix_sources_slug"), "sources", ["slug"], unique=False)

    op.create_table(
        "projects",
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("repo_url", sa.String(), nullable=True),
        sa.Column("live_url", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "tags",
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_tags_name"), "tags", ["name"], unique=False)

    op.create_table(
        "technologies",
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_technologies_name"), "technologies", ["name"], unique=False)

    op.create_table(
        "users",
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )

    op.create_table(
        "scheduler_logs",
        sa.Column("job_name", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("items_processed", sa.Integer(), nullable=False),
        sa.Column("items_failed", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_scheduler_logs_job_name"), "scheduler_logs", ["job_name"], unique=False)

    op.create_table(
        "activities",
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", "external_id", name="uq_activity_source_external"),
    )
    op.create_index("ix_activities_raw_payload_gin", "activities", ["raw_payload"], unique=False, postgresql_using="gin")
    op.create_index("ix_activities_source_occurred", "activities", ["source_id", "occurred_at"], unique=False)
    op.create_index("ix_activities_status", "activities", ["status"], unique=False)

    op.create_table(
        "activity_projects",
        sa.Column("activity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["activity_id"], ["activities.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("activity_id", "project_id"),
    )
    op.create_table(
        "activity_tags",
        sa.Column("activity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tag_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["activity_id"], ["activities.id"]),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"]),
        sa.PrimaryKeyConstraint("activity_id", "tag_id"),
    )
    op.create_table(
        "activity_technologies",
        sa.Column("activity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("technology_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["activity_id"], ["activities.id"]),
        sa.ForeignKeyConstraint(["technology_id"], ["technologies.id"]),
        sa.PrimaryKeyConstraint("activity_id", "technology_id"),
    )
    op.create_table(
        "embeddings",
        sa.Column("activity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chroma_id", sa.String(), nullable=False),
        sa.Column("model_name", sa.String(), nullable=False),
        sa.Column("dims", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["activity_id"], ["activities.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("activity_id"),
    )

    op.execute(
        """
        INSERT INTO sources (id, slug, display_name, is_active)
        VALUES
          ('00000000-0000-4000-8000-000000000001', 'github', 'GitHub', true),
          ('00000000-0000-4000-8000-000000000002', 'x', 'X', true),
          ('00000000-0000-4000-8000-000000000003', 'linkedin', 'LinkedIn', false)
        """
    )


def downgrade() -> None:
    """Drop all Abdul Core v1 tables."""

    op.drop_table("embeddings")
    op.drop_table("activity_technologies")
    op.drop_table("activity_tags")
    op.drop_table("activity_projects")
    op.drop_index("ix_activities_status", table_name="activities")
    op.drop_index("ix_activities_source_occurred", table_name="activities")
    op.drop_index("ix_activities_raw_payload_gin", table_name="activities", postgresql_using="gin")
    op.drop_table("activities")
    op.drop_index(op.f("ix_scheduler_logs_job_name"), table_name="scheduler_logs")
    op.drop_table("scheduler_logs")
    op.drop_table("users")
    op.drop_index(op.f("ix_technologies_name"), table_name="technologies")
    op.drop_table("technologies")
    op.drop_index(op.f("ix_tags_name"), table_name="tags")
    op.drop_table("tags")
    op.drop_table("projects")
    op.drop_index(op.f("ix_sources_slug"), table_name="sources")
    op.drop_table("sources")

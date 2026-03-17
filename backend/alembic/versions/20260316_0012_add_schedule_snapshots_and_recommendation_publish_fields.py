"""add schedule snapshots and recommendation publish/modify fields

Revision ID: 20260316_0012
Revises: 20260316_0011
Create Date: 2026-03-16 20:12:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260316_0012"
down_revision = "20260316_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agentic_schedule_recommendations",
        sa.Column("published_by", sa.Integer(), nullable=True),
    )
    op.add_column(
        "agentic_schedule_recommendations",
        sa.Column("published_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "agentic_schedule_recommendations",
        sa.Column("source_recommendation_id", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "agentic_schedule_recommendations",
        sa.Column("revision_number", sa.Integer(), nullable=False, server_default="1"),
    )

    op.create_foreign_key(
        "fk_agentic_sched_rec_published_by",
        "agentic_schedule_recommendations",
        "users",
        ["published_by"],
        ["id"],
    )

    op.create_foreign_key(
        "fk_agentic_sched_rec_source_recommendation",
        "agentic_schedule_recommendations",
        "agentic_schedule_recommendations",
        ["source_recommendation_id"],
        ["recommendation_id"],
    )

    op.create_check_constraint(
        "ck_agentic_sched_rec_state_v2",
        "agentic_schedule_recommendations",
        "state IN ('RECEIVED', 'CLASSIFIED', 'PLANNED', 'VALIDATED', 'OPTIMIZED', 'SIMULATED', "
        "'PENDING_APPROVAL', 'APPROVED', 'REJECTED', 'PUBLISHED', 'FAILED')",
    )
    op.drop_constraint("ck_agentic_sched_rec_state", "agentic_schedule_recommendations", type_="check")
    op.alter_column("agentic_schedule_recommendations", "state", server_default="SIMULATED")

    op.create_check_constraint(
        "ck_agentic_sched_rec_status_v2",
        "agentic_schedule_recommendations",
        "status IN ('pending_approval', 'approved', 'rejected', 'published')",
    )
    op.drop_constraint("ck_agentic_sched_rec_status", "agentic_schedule_recommendations", type_="check")

    op.create_index(
        "ix_agentic_sched_rec_source_rec",
        "agentic_schedule_recommendations",
        ["source_recommendation_id"],
        unique=False,
    )
    op.create_index(
        "ix_agentic_sched_rec_revision",
        "agentic_schedule_recommendations",
        ["recommendation_id", "revision_number"],
        unique=False,
    )

    op.create_table(
        "production_schedule_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("supply_plan_id", sa.Integer(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("recommendation_id", sa.String(length=64), nullable=True),
        sa.Column("snapshot_json", sa.Text(), nullable=False),
        sa.Column("published_by", sa.Integer(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["published_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["supply_plan_id"], ["supply_plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("supply_plan_id", "version_number", name="uq_schedule_snapshot_supply_plan_version"),
    )
    op.create_index("ix_production_schedule_snapshots_id", "production_schedule_snapshots", ["id"], unique=False)
    op.create_index(
        "ix_schedule_snapshot_supply_plan",
        "production_schedule_snapshots",
        ["supply_plan_id"],
        unique=False,
    )
    op.create_index(
        "ix_schedule_snapshot_recommendation",
        "production_schedule_snapshots",
        ["recommendation_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_schedule_snapshot_recommendation", table_name="production_schedule_snapshots")
    op.drop_index("ix_schedule_snapshot_supply_plan", table_name="production_schedule_snapshots")
    op.drop_index("ix_production_schedule_snapshots_id", table_name="production_schedule_snapshots")
    op.drop_table("production_schedule_snapshots")

    op.drop_index("ix_agentic_sched_rec_revision", table_name="agentic_schedule_recommendations")
    op.drop_index("ix_agentic_sched_rec_source_rec", table_name="agentic_schedule_recommendations")

    op.create_check_constraint(
        "ck_agentic_sched_rec_status",
        "agentic_schedule_recommendations",
        "status IN ('pending_approval', 'approved', 'rejected')",
    )
    op.drop_constraint("ck_agentic_sched_rec_status_v2", "agentic_schedule_recommendations", type_="check")

    op.alter_column("agentic_schedule_recommendations", "state", server_default="PENDING_APPROVAL")
    op.create_check_constraint(
        "ck_agentic_sched_rec_state",
        "agentic_schedule_recommendations",
        "state IN ('RECEIVED', 'CLASSIFIED', 'PENDING_APPROVAL', 'APPROVED', 'REJECTED')",
    )
    op.drop_constraint("ck_agentic_sched_rec_state_v2", "agentic_schedule_recommendations", type_="check")

    op.drop_constraint("fk_agentic_sched_rec_source_recommendation", "agentic_schedule_recommendations", type_="foreignkey")
    op.drop_constraint("fk_agentic_sched_rec_published_by", "agentic_schedule_recommendations", type_="foreignkey")

    op.drop_column("agentic_schedule_recommendations", "revision_number")
    op.drop_column("agentic_schedule_recommendations", "source_recommendation_id")
    op.drop_column("agentic_schedule_recommendations", "published_at")
    op.drop_column("agentic_schedule_recommendations", "published_by")

"""add agentic schedule recommendations table

Revision ID: 20260316_0011
Revises: 20260302_0010
Create Date: 2026-03-16 19:48:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260316_0011"
down_revision = "20260302_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agentic_schedule_recommendations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("recommendation_id", sa.String(length=64), nullable=False),
        sa.Column("workflow_id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(), nullable=False),
        sa.Column("supply_plan_id", sa.Integer(), nullable=True),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("period", sa.Date(), nullable=True),
        sa.Column("workcenter", sa.String(length=100), nullable=True),
        sa.Column("line", sa.String(length=100), nullable=True),
        sa.Column("shift", sa.String(length=50), nullable=True),
        sa.Column("impacted_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recommendation_summary", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("actions_json", sa.Text(), nullable=False),
        sa.Column("state", sa.String(length=30), nullable=False, server_default="PENDING_APPROVAL"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending_approval"),
        sa.Column("decision_note", sa.Text(), nullable=True),
        sa.Column("decided_by", sa.Integer(), nullable=True),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["decided_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["supply_plan_id"], ["supply_plans.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("recommendation_id"),
        sa.UniqueConstraint("workflow_id"),
        sa.CheckConstraint(
            "event_type IN ('MACHINE_DOWN', 'MACHINE_RECOVERED', 'ORDER_PRIORITY_CHANGED', "
            "'MATERIAL_SHORTAGE', 'QUALITY_HOLD', 'QUALITY_RELEASED', 'LABOR_UNAVAILABLE')",
            name="ck_agentic_sched_rec_event_type",
        ),
        sa.CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="ck_agentic_sched_rec_severity",
        ),
        sa.CheckConstraint(
            "state IN ('RECEIVED', 'CLASSIFIED', 'PENDING_APPROVAL', 'APPROVED', 'REJECTED')",
            name="ck_agentic_sched_rec_state",
        ),
        sa.CheckConstraint(
            "status IN ('pending_approval', 'approved', 'rejected')",
            name="ck_agentic_sched_rec_status",
        ),
    )

    op.create_index(
        "ix_agentic_schedule_recommendations_id",
        "agentic_schedule_recommendations",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_agentic_schedule_recommendations_recommendation_id",
        "agentic_schedule_recommendations",
        ["recommendation_id"],
        unique=True,
    )
    op.create_index(
        "ix_agentic_schedule_recommendations_workflow_id",
        "agentic_schedule_recommendations",
        ["workflow_id"],
        unique=True,
    )
    op.create_index(
        "ix_agentic_sched_rec_status_created",
        "agentic_schedule_recommendations",
        ["status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_agentic_sched_rec_supply_plan_status",
        "agentic_schedule_recommendations",
        ["supply_plan_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_agentic_sched_rec_product_period",
        "agentic_schedule_recommendations",
        ["product_id", "period"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_agentic_sched_rec_product_period", table_name="agentic_schedule_recommendations")
    op.drop_index("ix_agentic_sched_rec_supply_plan_status", table_name="agentic_schedule_recommendations")
    op.drop_index("ix_agentic_sched_rec_status_created", table_name="agentic_schedule_recommendations")
    op.drop_index("ix_agentic_schedule_recommendations_workflow_id", table_name="agentic_schedule_recommendations")
    op.drop_index(
        "ix_agentic_schedule_recommendations_recommendation_id",
        table_name="agentic_schedule_recommendations",
    )
    op.drop_index("ix_agentic_schedule_recommendations_id", table_name="agentic_schedule_recommendations")
    op.drop_table("agentic_schedule_recommendations")

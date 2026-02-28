"""add production schedules table

Revision ID: 20260228_0007
Revises: 20260227_0006
Create Date: 2026-02-28 14:58:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260228_0007"
down_revision = "20260227_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "production_schedules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("supply_plan_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("workcenter", sa.String(length=100), nullable=False),
        sa.Column("line", sa.String(length=100), nullable=False),
        sa.Column("shift", sa.String(length=50), nullable=False),
        sa.Column("sequence_order", sa.Integer(), nullable=False),
        sa.Column("planned_qty", sa.Numeric(12, 2), nullable=False),
        sa.Column("planned_start_at", sa.DateTime(), nullable=False),
        sa.Column("planned_end_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["supply_plan_id"], ["supply_plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "supply_plan_id",
            "workcenter",
            "line",
            "shift",
            "sequence_order",
            name="uq_production_schedule_slot_sequence",
        ),
        sa.CheckConstraint("planned_qty >= 0", name="ck_production_schedules_planned_qty_non_negative"),
        sa.CheckConstraint("sequence_order >= 1", name="ck_production_schedules_sequence_min_1"),
        sa.CheckConstraint(
            "status IN ('draft', 'released', 'in_progress', 'completed')",
            name="ck_production_schedules_status",
        ),
    )
    op.create_index("ix_production_schedules_id", "production_schedules", ["id"], unique=False)
    op.create_index(
        "ix_production_schedules_product_period",
        "production_schedules",
        ["product_id", "period"],
        unique=False,
    )
    op.create_index(
        "ix_production_schedules_workcenter_line_shift",
        "production_schedules",
        ["workcenter", "line", "shift"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_production_schedules_workcenter_line_shift", table_name="production_schedules")
    op.drop_index("ix_production_schedules_product_period", table_name="production_schedules")
    op.drop_index("ix_production_schedules_id", table_name="production_schedules")
    op.drop_table("production_schedules")

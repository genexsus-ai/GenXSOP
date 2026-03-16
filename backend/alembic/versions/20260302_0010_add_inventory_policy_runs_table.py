"""add inventory policy runs table

Revision ID: 20260302_0010
Revises: 20260301_0009
Create Date: 2026-03-02 12:35:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260302_0010"
down_revision = "20260301_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inventory_policy_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=True),
        sa.Column("location", sa.String(length=100), nullable=True),
        sa.Column("requested_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("parameters_json", sa.Text(), nullable=True),
        sa.Column("result_json", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("processed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("exception_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "status IN ('running', 'completed', 'failed')",
            name="ck_inventory_policy_runs_status",
        ),
    )

    op.create_index("ix_inventory_policy_runs_run_id", "inventory_policy_runs", ["run_id"], unique=True)
    op.create_index("ix_inventory_policy_runs_status", "inventory_policy_runs", ["status"], unique=False)
    op.create_index("ix_inventory_policy_runs_product_id", "inventory_policy_runs", ["product_id"], unique=False)
    op.create_index("ix_inventory_policy_runs_location", "inventory_policy_runs", ["location"], unique=False)
    op.create_index("ix_inventory_policy_runs_requested_by", "inventory_policy_runs", ["requested_by"], unique=False)
    op.create_index(
        "ix_inventory_policy_runs_status_created",
        "inventory_policy_runs",
        ["status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_inventory_policy_runs_requested_by_created",
        "inventory_policy_runs",
        ["requested_by", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_inventory_policy_runs_requested_by_created", table_name="inventory_policy_runs")
    op.drop_index("ix_inventory_policy_runs_status_created", table_name="inventory_policy_runs")
    op.drop_index("ix_inventory_policy_runs_requested_by", table_name="inventory_policy_runs")
    op.drop_index("ix_inventory_policy_runs_location", table_name="inventory_policy_runs")
    op.drop_index("ix_inventory_policy_runs_product_id", table_name="inventory_policy_runs")
    op.drop_index("ix_inventory_policy_runs_status", table_name="inventory_policy_runs")
    op.drop_index("ix_inventory_policy_runs_run_id", table_name="inventory_policy_runs")
    op.drop_table("inventory_policy_runs")

"""add inventory policy exceptions table

Revision ID: 20260301_0008
Revises: 20260228_0007
Create Date: 2026-03-01 17:45:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260301_0008"
down_revision = "20260228_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inventory_policy_exceptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("inventory_id", sa.Integer(), nullable=False),
        sa.Column("exception_type", sa.String(length=30), nullable=False),
        sa.Column("severity", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("recommended_action", sa.Text(), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["inventory_id"], ["inventory.id"]),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "exception_type IN ('stockout_risk', 'excess_risk', 'data_quality_risk')",
            name="ck_inventory_policy_exception_type",
        ),
        sa.CheckConstraint(
            "severity IN ('low', 'medium', 'high')",
            name="ck_inventory_policy_exception_severity",
        ),
        sa.CheckConstraint(
            "status IN ('open', 'in_progress', 'resolved', 'dismissed')",
            name="ck_inventory_policy_exception_status",
        ),
    )
    op.create_index(
        "ix_inventory_policy_exceptions_status_due",
        "inventory_policy_exceptions",
        ["status", "due_date"],
        unique=False,
    )
    op.create_index(
        "ix_inventory_policy_exceptions_inventory_type",
        "inventory_policy_exceptions",
        ["inventory_id", "exception_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_inventory_policy_exceptions_inventory_type", table_name="inventory_policy_exceptions")
    op.drop_index("ix_inventory_policy_exceptions_status_due", table_name="inventory_policy_exceptions")
    op.drop_table("inventory_policy_exceptions")

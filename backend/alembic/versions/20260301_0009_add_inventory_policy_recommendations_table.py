"""add inventory policy recommendations table

Revision ID: 20260301_0009
Revises: 20260301_0008
Create Date: 2026-03-01 18:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260301_0009"
down_revision = "20260301_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inventory_policy_recommendations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("inventory_id", sa.Integer(), nullable=False),
        sa.Column("recommended_safety_stock", sa.Numeric(12, 2), nullable=False),
        sa.Column("recommended_reorder_point", sa.Numeric(12, 2), nullable=False),
        sa.Column("recommended_max_stock", sa.Numeric(12, 2), nullable=True),
        sa.Column("confidence_score", sa.Numeric(5, 4), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("signals_json", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("decision_notes", sa.Text(), nullable=True),
        sa.Column("decided_by", sa.Integer(), nullable=True),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["inventory_id"], ["inventory.id"]),
        sa.ForeignKeyConstraint(["decided_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "status IN ('pending', 'accepted', 'rejected', 'applied')",
            name="ck_inventory_policy_recommendation_status",
        ),
        sa.CheckConstraint(
            "confidence_score >= 0 AND confidence_score <= 1",
            name="ck_inventory_policy_recommendation_confidence_range",
        ),
    )
    op.create_index(
        "ix_inventory_policy_recommendations_status_created",
        "inventory_policy_recommendations",
        ["status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_inventory_policy_recommendations_inventory_status",
        "inventory_policy_recommendations",
        ["inventory_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_inventory_policy_recommendations_inventory_status",
        table_name="inventory_policy_recommendations",
    )
    op.drop_index(
        "ix_inventory_policy_recommendations_status_created",
        table_name="inventory_policy_recommendations",
    )
    op.drop_table("inventory_policy_recommendations")

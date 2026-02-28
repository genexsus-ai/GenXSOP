"""add forecast consensus table

Revision ID: 20260227_0005
Revises: 20260227_0004
Create Date: 2026-02-27 20:36:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260227_0005"
down_revision = "20260227_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "forecast_consensus",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("baseline_qty", sa.Numeric(12, 2), nullable=False),
        sa.Column("sales_override_qty", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("marketing_uplift_qty", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("finance_adjustment_qty", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("constraint_cap_qty", sa.Numeric(12, 2), nullable=True),
        sa.Column("pre_consensus_qty", sa.Numeric(12, 2), nullable=False),
        sa.Column("final_consensus_qty", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("approved_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "product_id",
            "period",
            "version",
            name="uq_forecast_consensus_product_period_version",
        ),
        sa.CheckConstraint("baseline_qty >= 0", name="ck_forecast_consensus_baseline_non_negative"),
        sa.CheckConstraint(
            "constraint_cap_qty IS NULL OR constraint_cap_qty >= 0",
            name="ck_forecast_consensus_cap_non_negative",
        ),
        sa.CheckConstraint("pre_consensus_qty >= 0", name="ck_forecast_consensus_pre_non_negative"),
        sa.CheckConstraint("final_consensus_qty >= 0", name="ck_forecast_consensus_final_non_negative"),
        sa.CheckConstraint(
            "status IN ('draft', 'proposed', 'approved', 'frozen')",
            name="ck_forecast_consensus_status",
        ),
        sa.CheckConstraint("version >= 1", name="ck_forecast_consensus_version_min_1"),
    )

    op.create_index("ix_forecast_consensus_id", "forecast_consensus", ["id"], unique=False)
    op.create_index("ix_forecast_consensus_product_id", "forecast_consensus", ["product_id"], unique=False)
    op.create_index("ix_forecast_consensus_period", "forecast_consensus", ["period"], unique=False)
    op.create_index(
        "ix_forecast_consensus_product_period",
        "forecast_consensus",
        ["product_id", "period"],
        unique=False,
    )
    op.create_index(
        "ix_forecast_consensus_status_period",
        "forecast_consensus",
        ["status", "period"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_forecast_consensus_status_period", table_name="forecast_consensus")
    op.drop_index("ix_forecast_consensus_product_period", table_name="forecast_consensus")
    op.drop_index("ix_forecast_consensus_period", table_name="forecast_consensus")
    op.drop_index("ix_forecast_consensus_product_id", table_name="forecast_consensus")
    op.drop_index("ix_forecast_consensus_id", table_name="forecast_consensus")
    op.drop_table("forecast_consensus")

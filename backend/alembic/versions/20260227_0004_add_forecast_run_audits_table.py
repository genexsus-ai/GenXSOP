"""add forecast_run_audits table for diagnostics persistence

Revision ID: 20260227_0004
Revises: 20260227_0003
Create Date: 2026-02-27 15:54:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260227_0004"
down_revision = "20260227_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "forecast_run_audits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("requested_model", sa.String(length=50), nullable=True),
        sa.Column("selected_model", sa.String(length=50), nullable=False),
        sa.Column("horizon", sa.Integer(), nullable=False),
        sa.Column("advisor_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("fallback_used", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("advisor_confidence", sa.Numeric(6, 4), nullable=True),
        sa.Column("selection_reason", sa.Text(), nullable=True),
        sa.Column("history_months", sa.Integer(), nullable=False),
        sa.Column("records_created", sa.Integer(), nullable=False),
        sa.Column("warnings_json", sa.Text(), nullable=True),
        sa.Column("candidate_metrics_json", sa.Text(), nullable=True),
        sa.Column("data_quality_flags_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    op.create_index("ix_forecast_run_audits_id", "forecast_run_audits", ["id"], unique=False)
    op.create_index("ix_forecast_run_audits_product_id", "forecast_run_audits", ["product_id"], unique=False)
    op.create_index("ix_forecast_run_audits_user_id", "forecast_run_audits", ["user_id"], unique=False)
    op.create_index(
        "ix_forecast_run_audits_product_created",
        "forecast_run_audits",
        ["product_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_forecast_run_audits_fallback",
        "forecast_run_audits",
        ["fallback_used", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_forecast_run_audits_fallback", table_name="forecast_run_audits")
    op.drop_index("ix_forecast_run_audits_product_created", table_name="forecast_run_audits")
    op.drop_index("ix_forecast_run_audits_user_id", table_name="forecast_run_audits")
    op.drop_index("ix_forecast_run_audits_product_id", table_name="forecast_run_audits")
    op.drop_index("ix_forecast_run_audits_id", table_name="forecast_run_audits")
    op.drop_table("forecast_run_audits")
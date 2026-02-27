"""add forecast_jobs table

Revision ID: 20260227_0001
Revises:
Create Date: 2026-02-27 01:07:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260227_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "forecast_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("horizon", sa.Integer(), nullable=False),
        sa.Column("model_type", sa.String(length=50), nullable=True),
        sa.Column("requested_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("result_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_forecast_jobs_job_id", "forecast_jobs", ["job_id"], unique=True)
    op.create_index("ix_forecast_jobs_status", "forecast_jobs", ["status"], unique=False)
    op.create_index("ix_forecast_jobs_product_id", "forecast_jobs", ["product_id"], unique=False)
    op.create_index("ix_forecast_jobs_requested_by", "forecast_jobs", ["requested_by"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_forecast_jobs_requested_by", table_name="forecast_jobs")
    op.drop_index("ix_forecast_jobs_product_id", table_name="forecast_jobs")
    op.drop_index("ix_forecast_jobs_status", table_name="forecast_jobs")
    op.drop_index("ix_forecast_jobs_job_id", table_name="forecast_jobs")
    op.drop_table("forecast_jobs")

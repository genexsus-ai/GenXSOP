"""link forecast consensus rows to forecast run audits

Revision ID: 20260227_0006
Revises: 20260227_0005
Create Date: 2026-02-27 22:10:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260227_0006"
down_revision = "20260227_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "forecast_consensus",
        sa.Column("forecast_run_audit_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_forecast_consensus_run_audit",
        "forecast_consensus",
        "forecast_run_audits",
        ["forecast_run_audit_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_forecast_consensus_forecast_run_audit_id",
        "forecast_consensus",
        ["forecast_run_audit_id"],
        unique=False,
    )
    op.create_index(
        "ix_forecast_consensus_run_period",
        "forecast_consensus",
        ["forecast_run_audit_id", "period"],
        unique=False,
    )

    op.drop_constraint(
        "uq_forecast_consensus_product_period_version",
        "forecast_consensus",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_forecast_consensus_run_period_version",
        "forecast_consensus",
        ["forecast_run_audit_id", "period", "version"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_forecast_consensus_run_period_version",
        "forecast_consensus",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_forecast_consensus_product_period_version",
        "forecast_consensus",
        ["product_id", "period", "version"],
    )

    op.drop_index("ix_forecast_consensus_run_period", table_name="forecast_consensus")
    op.drop_index("ix_forecast_consensus_forecast_run_audit_id", table_name="forecast_consensus")
    op.drop_constraint(
        "fk_forecast_consensus_run_audit",
        "forecast_consensus",
        type_="foreignkey",
    )
    op.drop_column("forecast_consensus", "forecast_run_audit_id")

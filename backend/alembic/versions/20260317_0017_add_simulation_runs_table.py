"""add simulation runs table for persisted what-if execution

Revision ID: 20260317_0017
Revises: 20260317_0016
Create Date: 2026-03-17 02:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260317_0017"
down_revision = "20260317_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "simulation_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("simulation_id", sa.String(length=64), nullable=False),
        sa.Column("recommendation_id", sa.String(length=64), nullable=True),
        sa.Column("scenario_name", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="completed"),
        sa.Column("request_json", sa.Text(), nullable=True),
        sa.Column("result_json", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["recommendation_id"], ["agentic_schedule_recommendations.recommendation_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("simulation_id"),
        sa.CheckConstraint("status IN ('completed', 'failed')", name="ck_simulation_runs_status"),
    )

    op.create_index("ix_simulation_runs_id", "simulation_runs", ["id"], unique=False)
    op.create_index("ix_simulation_runs_simulation_id", "simulation_runs", ["simulation_id"], unique=False)
    op.create_index("ix_simulation_runs_recommendation_id", "simulation_runs", ["recommendation_id"], unique=False)
    op.create_index("ix_simulation_runs_created_by", "simulation_runs", ["created_by"], unique=False)
    op.create_index("ix_simulation_runs_status_created", "simulation_runs", ["status", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_simulation_runs_status_created", table_name="simulation_runs")
    op.drop_index("ix_simulation_runs_created_by", table_name="simulation_runs")
    op.drop_index("ix_simulation_runs_recommendation_id", table_name="simulation_runs")
    op.drop_index("ix_simulation_runs_simulation_id", table_name="simulation_runs")
    op.drop_index("ix_simulation_runs_id", table_name="simulation_runs")
    op.drop_table("simulation_runs")

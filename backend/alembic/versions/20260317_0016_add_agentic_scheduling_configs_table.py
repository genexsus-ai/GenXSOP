"""add agentic scheduling configs table for objectives and policies

Revision ID: 20260317_0016
Revises: 20260317_0015
Create Date: 2026-03-17 01:37:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260317_0016"
down_revision = "20260317_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agentic_scheduling_configs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("config_type", sa.String(length=20), nullable=False),
        sa.Column("scope", sa.String(length=30), nullable=False, server_default="global"),
        sa.Column("name", sa.String(length=100), nullable=False, server_default="default"),
        sa.Column("config_json", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("config_type", "scope", "name", name="uq_agentic_sched_cfg_type_scope_name"),
        sa.CheckConstraint("config_type IN ('objectives', 'policies')", name="ck_agentic_sched_cfg_type"),
    )

    op.create_index("ix_agentic_scheduling_configs_id", "agentic_scheduling_configs", ["id"], unique=False)
    op.create_index(
        "ix_agentic_scheduling_configs_config_type",
        "agentic_scheduling_configs",
        ["config_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_agentic_scheduling_configs_config_type", table_name="agentic_scheduling_configs")
    op.drop_index("ix_agentic_scheduling_configs_id", table_name="agentic_scheduling_configs")
    op.drop_table("agentic_scheduling_configs")

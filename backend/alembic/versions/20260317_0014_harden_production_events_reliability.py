"""harden production events reliability fields and status checks

Revision ID: 20260317_0014
Revises: 20260316_0013
Create Date: 2026-03-17 01:10:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260317_0014"
down_revision = "20260316_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("production_events") as batch_op:
        batch_op.add_column(sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("max_retries", sa.Integer(), nullable=False, server_default="3"))
        batch_op.add_column(sa.Column("out_of_order", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("dead_letter_reason", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("dead_lettered_at", sa.DateTime(), nullable=True))

        batch_op.drop_constraint("ck_production_events_processing_status", type_="check")
        batch_op.create_check_constraint(
            "ck_production_events_processing_status",
            "processing_status IN ('RECEIVED', 'NORMALIZED', 'PROCESSED', 'FAILED', 'REPLAYED', 'OUT_OF_ORDER', 'DEAD_LETTER')",
        )


def downgrade() -> None:
    with op.batch_alter_table("production_events") as batch_op:
        batch_op.drop_constraint("ck_production_events_processing_status", type_="check")
        batch_op.create_check_constraint(
            "ck_production_events_processing_status",
            "processing_status IN ('RECEIVED', 'NORMALIZED', 'PROCESSED', 'FAILED', 'REPLAYED')",
        )

        batch_op.drop_column("dead_lettered_at")
        batch_op.drop_column("dead_letter_reason")
        batch_op.drop_column("out_of_order")
        batch_op.drop_column("max_retries")
        batch_op.drop_column("retry_count")

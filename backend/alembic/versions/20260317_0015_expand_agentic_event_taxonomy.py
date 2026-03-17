"""expand agentic recommendation event taxonomy for phase-1 canonical events

Revision ID: 20260317_0015
Revises: 20260317_0014
Create Date: 2026-03-17 01:16:00
"""

from alembic import op


revision = "20260317_0015"
down_revision = "20260317_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("agentic_schedule_recommendations") as batch_op:
        batch_op.drop_constraint("ck_agentic_sched_rec_event_type", type_="check")
        batch_op.create_check_constraint(
            "ck_agentic_sched_rec_event_type",
            "event_type IN ('MACHINE_DOWN', 'MACHINE_RECOVERED', 'ORDER_PRIORITY_CHANGED', "
            "'MATERIAL_SHORTAGE', 'QUALITY_HOLD', 'QUALITY_RELEASED', 'LABOR_UNAVAILABLE', "
            "'DOWNTIME_PLANNED', 'WIP_UPDATED', 'ORDER_RELEASED')",
        )


def downgrade() -> None:
    with op.batch_alter_table("agentic_schedule_recommendations") as batch_op:
        batch_op.drop_constraint("ck_agentic_sched_rec_event_type", type_="check")
        batch_op.create_check_constraint(
            "ck_agentic_sched_rec_event_type",
            "event_type IN ('MACHINE_DOWN', 'MACHINE_RECOVERED', 'ORDER_PRIORITY_CHANGED', "
            "'MATERIAL_SHORTAGE', 'QUALITY_HOLD', 'QUALITY_RELEASED', 'LABOR_UNAVAILABLE')",
        )

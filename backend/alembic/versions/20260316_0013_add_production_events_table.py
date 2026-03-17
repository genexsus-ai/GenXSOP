"""add production events table for canonical ingest and replay

Revision ID: 20260316_0013
Revises: 20260316_0012
Create Date: 2026-03-16 20:25:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260316_0013"
down_revision = "20260316_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "production_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("event_source", sa.String(length=20), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(), nullable=False),
        sa.Column("plant_id", sa.String(length=64), nullable=True),
        sa.Column("line_id", sa.String(length=64), nullable=True),
        sa.Column("resource_id", sa.String(length=64), nullable=True),
        sa.Column("order_id", sa.String(length=64), nullable=True),
        sa.Column("severity", sa.String(length=20), nullable=False, server_default="medium"),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("normalized_json", sa.Text(), nullable=True),
        sa.Column("correlation_id", sa.String(length=128), nullable=True),
        sa.Column("trace_id", sa.String(length=128), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("duplicate_of_event_id", sa.String(length=64), nullable=True),
        sa.Column("processing_status", sa.String(length=20), nullable=False, server_default="RECEIVED"),
        sa.Column("replay_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("received_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
        sa.UniqueConstraint("idempotency_key"),
        sa.CheckConstraint(
            "event_source IN ('ERP', 'MES', 'IIOT', 'QMS', 'CMMS', 'MANUAL')",
            name="ck_production_events_source",
        ),
        sa.CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="ck_production_events_severity",
        ),
        sa.CheckConstraint(
            "processing_status IN ('RECEIVED', 'NORMALIZED', 'PROCESSED', 'FAILED', 'REPLAYED')",
            name="ck_production_events_processing_status",
        ),
    )

    op.create_index("ix_production_events_id", "production_events", ["id"], unique=False)
    op.create_index("ix_production_events_event_id", "production_events", ["event_id"], unique=True)
    op.create_index("ix_production_events_event_type", "production_events", ["event_type"], unique=False)
    op.create_index("ix_production_events_event_source", "production_events", ["event_source"], unique=False)
    op.create_index("ix_production_events_event_timestamp", "production_events", ["event_timestamp"], unique=False)
    op.create_index("ix_production_events_plant_id", "production_events", ["plant_id"], unique=False)
    op.create_index("ix_production_events_line_id", "production_events", ["line_id"], unique=False)
    op.create_index("ix_production_events_resource_id", "production_events", ["resource_id"], unique=False)
    op.create_index("ix_production_events_order_id", "production_events", ["order_id"], unique=False)
    op.create_index("ix_production_events_idempotency_key", "production_events", ["idempotency_key"], unique=True)
    op.create_index("ix_production_events_source_ts", "production_events", ["event_source", "event_timestamp"], unique=False)
    op.create_index("ix_production_events_correlation", "production_events", ["correlation_id"], unique=False)
    op.create_index("ix_production_events_trace", "production_events", ["trace_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_production_events_trace", table_name="production_events")
    op.drop_index("ix_production_events_correlation", table_name="production_events")
    op.drop_index("ix_production_events_source_ts", table_name="production_events")
    op.drop_index("ix_production_events_idempotency_key", table_name="production_events")
    op.drop_index("ix_production_events_order_id", table_name="production_events")
    op.drop_index("ix_production_events_resource_id", table_name="production_events")
    op.drop_index("ix_production_events_line_id", table_name="production_events")
    op.drop_index("ix_production_events_plant_id", table_name="production_events")
    op.drop_index("ix_production_events_event_timestamp", table_name="production_events")
    op.drop_index("ix_production_events_event_source", table_name="production_events")
    op.drop_index("ix_production_events_event_type", table_name="production_events")
    op.drop_index("ix_production_events_event_id", table_name="production_events")
    op.drop_index("ix_production_events_id", table_name="production_events")
    op.drop_table("production_events")

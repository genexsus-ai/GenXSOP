"""data quality backfill for enterprise constraints

Revision ID: 20260227_0003
Revises: 20260227_0002
Create Date: 2026-02-27 02:05:00
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "20260227_0003"
down_revision = "20260227_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Demand plans normalization
    op.execute("UPDATE demand_plans SET region = 'Global' WHERE region IS NULL OR TRIM(region) = ''")
    op.execute("UPDATE demand_plans SET channel = 'All' WHERE channel IS NULL OR TRIM(channel) = ''")
    op.execute("UPDATE demand_plans SET status = 'draft' WHERE status IS NULL OR status NOT IN ('draft','submitted','approved')")
    op.execute("UPDATE demand_plans SET version = 1 WHERE version IS NULL OR version < 1")
    op.execute("UPDATE demand_plans SET forecast_qty = 0 WHERE forecast_qty < 0")
    op.execute("UPDATE demand_plans SET adjusted_qty = 0 WHERE adjusted_qty < 0")
    op.execute("UPDATE demand_plans SET actual_qty = 0 WHERE actual_qty < 0")
    op.execute("UPDATE demand_plans SET consensus_qty = 0 WHERE consensus_qty < 0")
    op.execute("UPDATE demand_plans SET confidence = 0 WHERE confidence < 0")
    op.execute("UPDATE demand_plans SET confidence = 100 WHERE confidence > 100")

    # Supply plans normalization
    op.execute("UPDATE supply_plans SET location = 'Main' WHERE location IS NULL OR TRIM(location) = ''")
    op.execute("UPDATE supply_plans SET status = 'draft' WHERE status IS NULL OR status NOT IN ('draft','submitted','approved')")
    op.execute("UPDATE supply_plans SET version = 1 WHERE version IS NULL OR version < 1")
    op.execute("UPDATE supply_plans SET planned_prod_qty = 0 WHERE planned_prod_qty < 0")
    op.execute("UPDATE supply_plans SET actual_prod_qty = 0 WHERE actual_prod_qty < 0")
    op.execute("UPDATE supply_plans SET capacity_max = 0 WHERE capacity_max < 0")
    op.execute("UPDATE supply_plans SET capacity_used = 0 WHERE capacity_used < 0")
    op.execute("UPDATE supply_plans SET capacity_used = 100 WHERE capacity_used > 100")
    op.execute("UPDATE supply_plans SET lead_time_days = 0 WHERE lead_time_days < 0")
    op.execute("UPDATE supply_plans SET cost_per_unit = 0 WHERE cost_per_unit < 0")

    # Forecasts normalization
    op.execute("UPDATE forecasts SET predicted_qty = 0 WHERE predicted_qty < 0")
    op.execute("UPDATE forecasts SET lower_bound = 0 WHERE lower_bound < 0")
    op.execute("UPDATE forecasts SET upper_bound = 0 WHERE upper_bound < 0")
    op.execute("UPDATE forecasts SET confidence = 0 WHERE confidence < 0")
    op.execute("UPDATE forecasts SET confidence = 100 WHERE confidence > 100")
    op.execute("UPDATE forecasts SET mape = 0 WHERE mape < 0")
    op.execute("UPDATE forecasts SET rmse = 0 WHERE rmse < 0")

    # Inventory normalization
    op.execute("UPDATE inventory SET location = 'Main' WHERE location IS NULL OR TRIM(location) = ''")
    op.execute("UPDATE inventory SET status = 'normal' WHERE status IS NULL OR status NOT IN ('normal','low','critical','excess')")
    op.execute("UPDATE inventory SET on_hand_qty = 0 WHERE on_hand_qty < 0")
    op.execute("UPDATE inventory SET allocated_qty = 0 WHERE allocated_qty < 0")
    op.execute("UPDATE inventory SET in_transit_qty = 0 WHERE in_transit_qty < 0")
    op.execute("UPDATE inventory SET safety_stock = 0 WHERE safety_stock < 0")
    op.execute("UPDATE inventory SET reorder_point = 0 WHERE reorder_point < 0")
    op.execute("UPDATE inventory SET max_stock = 0 WHERE max_stock < 0")
    op.execute("UPDATE inventory SET days_of_supply = 0 WHERE days_of_supply < 0")
    op.execute("UPDATE inventory SET valuation = 0 WHERE valuation < 0")

    # Scenario normalization
    op.execute("UPDATE scenarios SET scenario_type = 'what_if' WHERE scenario_type IS NULL OR scenario_type NOT IN ('what_if','baseline','stress_test')")
    op.execute("UPDATE scenarios SET status = 'draft' WHERE status IS NULL OR status NOT IN ('draft','submitted','completed','approved','rejected')")

    # Forecast jobs normalization
    op.execute("UPDATE forecast_jobs SET status = 'failed' WHERE status IS NULL OR status NOT IN ('queued','running','completed','failed','cancelled')")
    op.execute("UPDATE forecast_jobs SET horizon = 1 WHERE horizon IS NULL OR horizon < 1")


def downgrade() -> None:
    # Data normalization is intentionally non-reversible.
    pass

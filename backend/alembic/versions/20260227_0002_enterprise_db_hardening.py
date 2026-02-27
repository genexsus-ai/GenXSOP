"""enterprise db hardening constraints and indexes

Revision ID: 20260227_0002
Revises: 20260227_0001
Create Date: 2026-02-27 01:45:00
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "20260227_0002"
down_revision = "20260227_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("demand_plans") as batch_op:
        batch_op.create_unique_constraint(
            "uq_demand_plans_business_key",
            ["product_id", "period", "region", "channel", "version"],
        )
        batch_op.create_check_constraint(
            "ck_demand_plans_status",
            "status IN ('draft', 'submitted', 'approved')",
        )
        batch_op.create_check_constraint(
            "ck_demand_plans_forecast_qty_non_negative",
            "forecast_qty >= 0",
        )
        batch_op.create_check_constraint(
            "ck_demand_plans_adjusted_qty_non_negative",
            "adjusted_qty IS NULL OR adjusted_qty >= 0",
        )
        batch_op.create_check_constraint(
            "ck_demand_plans_actual_qty_non_negative",
            "actual_qty IS NULL OR actual_qty >= 0",
        )
        batch_op.create_check_constraint(
            "ck_demand_plans_consensus_qty_non_negative",
            "consensus_qty IS NULL OR consensus_qty >= 0",
        )
        batch_op.create_check_constraint(
            "ck_demand_plans_confidence_range",
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 100)",
        )
        batch_op.create_check_constraint(
            "ck_demand_plans_version_min_1",
            "version >= 1",
        )

    op.create_index("ix_demand_plans_status_period", "demand_plans", ["status", "period"], unique=False)
    op.create_index("ix_demand_plans_product_period", "demand_plans", ["product_id", "period"], unique=False)

    with op.batch_alter_table("supply_plans") as batch_op:
        batch_op.create_unique_constraint(
            "uq_supply_plans_business_key",
            ["product_id", "period", "location", "version"],
        )
        batch_op.create_check_constraint(
            "ck_supply_plans_status",
            "status IN ('draft', 'submitted', 'approved')",
        )
        batch_op.create_check_constraint(
            "ck_supply_plans_planned_qty_non_negative",
            "planned_prod_qty IS NULL OR planned_prod_qty >= 0",
        )
        batch_op.create_check_constraint(
            "ck_supply_plans_actual_qty_non_negative",
            "actual_prod_qty IS NULL OR actual_prod_qty >= 0",
        )
        batch_op.create_check_constraint(
            "ck_supply_plans_capacity_max_non_negative",
            "capacity_max IS NULL OR capacity_max >= 0",
        )
        batch_op.create_check_constraint(
            "ck_supply_plans_capacity_used_range",
            "capacity_used IS NULL OR (capacity_used >= 0 AND capacity_used <= 100)",
        )
        batch_op.create_check_constraint(
            "ck_supply_plans_lead_time_non_negative",
            "lead_time_days IS NULL OR lead_time_days >= 0",
        )
        batch_op.create_check_constraint(
            "ck_supply_plans_cost_per_unit_non_negative",
            "cost_per_unit IS NULL OR cost_per_unit >= 0",
        )
        batch_op.create_check_constraint(
            "ck_supply_plans_version_min_1",
            "version >= 1",
        )

    op.create_index("ix_supply_plans_status_period", "supply_plans", ["status", "period"], unique=False)
    op.create_index("ix_supply_plans_product_period", "supply_plans", ["product_id", "period"], unique=False)

    with op.batch_alter_table("forecasts") as batch_op:
        batch_op.create_unique_constraint(
            "uq_forecasts_business_key",
            ["product_id", "period", "model_type"],
        )
        batch_op.create_check_constraint(
            "ck_forecasts_predicted_qty_non_negative",
            "predicted_qty >= 0",
        )
        batch_op.create_check_constraint(
            "ck_forecasts_lower_bound_non_negative",
            "lower_bound IS NULL OR lower_bound >= 0",
        )
        batch_op.create_check_constraint(
            "ck_forecasts_upper_bound_non_negative",
            "upper_bound IS NULL OR upper_bound >= 0",
        )
        batch_op.create_check_constraint(
            "ck_forecasts_confidence_range",
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 100)",
        )
        batch_op.create_check_constraint(
            "ck_forecasts_mape_non_negative",
            "mape IS NULL OR mape >= 0",
        )
        batch_op.create_check_constraint(
            "ck_forecasts_rmse_non_negative",
            "rmse IS NULL OR rmse >= 0",
        )

    op.create_index("ix_forecasts_product_period", "forecasts", ["product_id", "period"], unique=False)
    op.create_index("ix_forecasts_model_period", "forecasts", ["model_type", "period"], unique=False)

    with op.batch_alter_table("inventory") as batch_op:
        batch_op.create_unique_constraint(
            "uq_inventory_product_location",
            ["product_id", "location"],
        )
        batch_op.create_check_constraint(
            "ck_inventory_status",
            "status IN ('normal', 'low', 'critical', 'excess')",
        )
        batch_op.create_check_constraint(
            "ck_inventory_on_hand_non_negative",
            "on_hand_qty >= 0",
        )
        batch_op.create_check_constraint(
            "ck_inventory_allocated_non_negative",
            "allocated_qty >= 0",
        )
        batch_op.create_check_constraint(
            "ck_inventory_in_transit_non_negative",
            "in_transit_qty >= 0",
        )
        batch_op.create_check_constraint(
            "ck_inventory_safety_stock_non_negative",
            "safety_stock >= 0",
        )
        batch_op.create_check_constraint(
            "ck_inventory_reorder_point_non_negative",
            "reorder_point >= 0",
        )
        batch_op.create_check_constraint(
            "ck_inventory_max_stock_non_negative",
            "max_stock IS NULL OR max_stock >= 0",
        )
        batch_op.create_check_constraint(
            "ck_inventory_days_of_supply_non_negative",
            "days_of_supply IS NULL OR days_of_supply >= 0",
        )
        batch_op.create_check_constraint(
            "ck_inventory_valuation_non_negative",
            "valuation IS NULL OR valuation >= 0",
        )

    op.create_index("ix_inventory_status_location", "inventory", ["status", "location"], unique=False)

    with op.batch_alter_table("scenarios") as batch_op:
        batch_op.create_check_constraint(
            "ck_scenarios_status",
            "status IN ('draft', 'submitted', 'completed', 'approved', 'rejected')",
        )
        batch_op.create_check_constraint(
            "ck_scenarios_type",
            "scenario_type IN ('what_if', 'baseline', 'stress_test')",
        )

    op.create_index("ix_scenarios_status_created_at", "scenarios", ["status", "created_at"], unique=False)

    with op.batch_alter_table("forecast_jobs") as batch_op:
        batch_op.create_check_constraint(
            "ck_forecast_jobs_status",
            "status IN ('queued', 'running', 'completed', 'failed', 'cancelled')",
        )
        batch_op.create_check_constraint(
            "ck_forecast_jobs_horizon_min_1",
            "horizon >= 1",
        )

    op.create_index("ix_forecast_jobs_status_created_at", "forecast_jobs", ["status", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_forecast_jobs_status_created_at", table_name="forecast_jobs")
    with op.batch_alter_table("forecast_jobs") as batch_op:
        batch_op.drop_constraint("ck_forecast_jobs_horizon_min_1", type_="check")
        batch_op.drop_constraint("ck_forecast_jobs_status", type_="check")

    op.drop_index("ix_scenarios_status_created_at", table_name="scenarios")
    with op.batch_alter_table("scenarios") as batch_op:
        batch_op.drop_constraint("ck_scenarios_type", type_="check")
        batch_op.drop_constraint("ck_scenarios_status", type_="check")

    op.drop_index("ix_inventory_status_location", table_name="inventory")
    with op.batch_alter_table("inventory") as batch_op:
        batch_op.drop_constraint("ck_inventory_valuation_non_negative", type_="check")
        batch_op.drop_constraint("ck_inventory_days_of_supply_non_negative", type_="check")
        batch_op.drop_constraint("ck_inventory_max_stock_non_negative", type_="check")
        batch_op.drop_constraint("ck_inventory_reorder_point_non_negative", type_="check")
        batch_op.drop_constraint("ck_inventory_safety_stock_non_negative", type_="check")
        batch_op.drop_constraint("ck_inventory_in_transit_non_negative", type_="check")
        batch_op.drop_constraint("ck_inventory_allocated_non_negative", type_="check")
        batch_op.drop_constraint("ck_inventory_on_hand_non_negative", type_="check")
        batch_op.drop_constraint("ck_inventory_status", type_="check")
        batch_op.drop_constraint("uq_inventory_product_location", type_="unique")

    op.drop_index("ix_forecasts_model_period", table_name="forecasts")
    op.drop_index("ix_forecasts_product_period", table_name="forecasts")
    with op.batch_alter_table("forecasts") as batch_op:
        batch_op.drop_constraint("ck_forecasts_rmse_non_negative", type_="check")
        batch_op.drop_constraint("ck_forecasts_mape_non_negative", type_="check")
        batch_op.drop_constraint("ck_forecasts_confidence_range", type_="check")
        batch_op.drop_constraint("ck_forecasts_upper_bound_non_negative", type_="check")
        batch_op.drop_constraint("ck_forecasts_lower_bound_non_negative", type_="check")
        batch_op.drop_constraint("ck_forecasts_predicted_qty_non_negative", type_="check")
        batch_op.drop_constraint("uq_forecasts_business_key", type_="unique")

    op.drop_index("ix_supply_plans_product_period", table_name="supply_plans")
    op.drop_index("ix_supply_plans_status_period", table_name="supply_plans")
    with op.batch_alter_table("supply_plans") as batch_op:
        batch_op.drop_constraint("ck_supply_plans_version_min_1", type_="check")
        batch_op.drop_constraint("ck_supply_plans_cost_per_unit_non_negative", type_="check")
        batch_op.drop_constraint("ck_supply_plans_lead_time_non_negative", type_="check")
        batch_op.drop_constraint("ck_supply_plans_capacity_used_range", type_="check")
        batch_op.drop_constraint("ck_supply_plans_capacity_max_non_negative", type_="check")
        batch_op.drop_constraint("ck_supply_plans_actual_qty_non_negative", type_="check")
        batch_op.drop_constraint("ck_supply_plans_planned_qty_non_negative", type_="check")
        batch_op.drop_constraint("ck_supply_plans_status", type_="check")
        batch_op.drop_constraint("uq_supply_plans_business_key", type_="unique")

    op.drop_index("ix_demand_plans_product_period", table_name="demand_plans")
    op.drop_index("ix_demand_plans_status_period", table_name="demand_plans")
    with op.batch_alter_table("demand_plans") as batch_op:
        batch_op.drop_constraint("ck_demand_plans_version_min_1", type_="check")
        batch_op.drop_constraint("ck_demand_plans_confidence_range", type_="check")
        batch_op.drop_constraint("ck_demand_plans_consensus_qty_non_negative", type_="check")
        batch_op.drop_constraint("ck_demand_plans_actual_qty_non_negative", type_="check")
        batch_op.drop_constraint("ck_demand_plans_adjusted_qty_non_negative", type_="check")
        batch_op.drop_constraint("ck_demand_plans_forecast_qty_non_negative", type_="check")
        batch_op.drop_constraint("ck_demand_plans_status", type_="check")
        batch_op.drop_constraint("uq_demand_plans_business_key", type_="unique")
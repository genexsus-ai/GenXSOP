"""
Seed data script for GenXSOP
Run: python seed_data.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import random
from app.database import SessionLocal, create_tables
from app.models.user import User
from app.models.product import Product, Category
from app.models.demand_plan import DemandPlan
from app.models.supply_plan import SupplyPlan
from app.models.inventory import Inventory
from app.models.sop_cycle import SOPCycle
from app.models.kpi_metric import KPIMetric
from app.utils.security import get_password_hash


def seed():
    create_tables()
    db = SessionLocal()
    try:
        # ── Users ────────────────────────────────────────────────────────────
        users_data = [
            {"email": "admin@genxsop.com", "full_name": "Admin User", "role": "admin", "department": "IT"},
            {"email": "executive@genxsop.com", "full_name": "Sarah Johnson", "role": "executive", "department": "Executive"},
            {"email": "demand@genxsop.com", "full_name": "Mike Chen", "role": "demand_planner", "department": "Planning"},
            {"email": "supply@genxsop.com", "full_name": "Lisa Park", "role": "supply_planner", "department": "Operations"},
            {"email": "inventory@genxsop.com", "full_name": "Tom Wilson", "role": "inventory_manager", "department": "Warehouse"},
            {"email": "finance@genxsop.com", "full_name": "Emma Davis", "role": "finance_analyst", "department": "Finance"},
            {"email": "coordinator@genxsop.com", "full_name": "James Brown", "role": "sop_coordinator", "department": "Planning"},
            {"email": "viewer@genxsop.com", "full_name": "Anna Smith", "role": "viewer", "department": "Sales"},
        ]
        created_users = {}
        for u in users_data:
            existing = db.query(User).filter(User.email == u["email"]).first()
            if not existing:
                user = User(hashed_password=get_password_hash("Password123!"), **u)
                db.add(user)
                db.flush()
                created_users[u["role"]] = user
            else:
                created_users[u["role"]] = existing
        db.commit()
        print("✅ Users seeded")

        # ── Categories ───────────────────────────────────────────────────────
        cats_data = [
            {"name": "Electronics", "level": 0},
            {"name": "Apparel", "level": 0},
            {"name": "Food & Beverage", "level": 0},
        ]
        created_cats = {}
        for c in cats_data:
            existing = db.query(Category).filter(Category.name == c["name"]).first()
            if not existing:
                cat = Category(**c)
                db.add(cat)
                db.flush()
                created_cats[c["name"]] = cat
            else:
                created_cats[c["name"]] = existing
        db.commit()
        print("✅ Categories seeded")

        # ── Products ─────────────────────────────────────────────────────────
        products_data = [
            {"sku": "ELEC-001", "name": "Wireless Headphones Pro", "category_id": created_cats["Electronics"].id, "product_family": "Audio", "unit_cost": 45.00, "selling_price": 129.99, "lead_time_days": 14},
            {"sku": "ELEC-002", "name": "Smart Watch Series X", "category_id": created_cats["Electronics"].id, "product_family": "Wearables", "unit_cost": 120.00, "selling_price": 299.99, "lead_time_days": 21},
            {"sku": "ELEC-003", "name": "Bluetooth Speaker Mini", "category_id": created_cats["Electronics"].id, "product_family": "Audio", "unit_cost": 25.00, "selling_price": 79.99, "lead_time_days": 10},
            {"sku": "APRL-001", "name": "Performance Running Shoes", "category_id": created_cats["Apparel"].id, "product_family": "Footwear", "unit_cost": 35.00, "selling_price": 89.99, "lead_time_days": 30},
            {"sku": "APRL-002", "name": "Yoga Pants Premium", "category_id": created_cats["Apparel"].id, "product_family": "Activewear", "unit_cost": 18.00, "selling_price": 54.99, "lead_time_days": 21},
            {"sku": "FOOD-001", "name": "Protein Bar Variety Pack", "category_id": created_cats["Food & Beverage"].id, "product_family": "Nutrition", "unit_cost": 12.00, "selling_price": 29.99, "lead_time_days": 7},
            {"sku": "FOOD-002", "name": "Green Tea Premium Blend", "category_id": created_cats["Food & Beverage"].id, "product_family": "Beverages", "unit_cost": 8.00, "selling_price": 19.99, "lead_time_days": 7},
        ]
        created_products = []
        for p in products_data:
            existing = db.query(Product).filter(Product.sku == p["sku"]).first()
            if not existing:
                product = Product(**p)
                db.add(product)
                db.flush()
                created_products.append(product)
            else:
                created_products.append(existing)
        db.commit()
        print("✅ Products seeded")

        # ── Demand Plans (12 months history) ─────────────────────────────────
        planner = created_users.get("demand_planner")
        base_demands = [850, 920, 680, 1200, 950, 780, 620]
        today = date.today()
        for product, base_demand in zip(created_products, base_demands):
            for months_ago in range(12, 0, -1):
                period = (today - relativedelta(months=months_ago)).replace(day=1)
                seasonal_factor = 1.0 + 0.2 * (1 if period.month in [11, 12] else -0.1 if period.month in [1, 2] else 0)
                forecast_qty = round(base_demand * seasonal_factor * random.uniform(0.9, 1.1), 0)
                actual_qty = round(forecast_qty * random.uniform(0.85, 1.15), 0)
                existing = db.query(DemandPlan).filter(
                    DemandPlan.product_id == product.id,
                    DemandPlan.period == period,
                ).first()
                if not existing:
                    plan = DemandPlan(
                        product_id=product.id,
                        period=period,
                        forecast_qty=forecast_qty,
                        adjusted_qty=round(forecast_qty * 1.02, 0),
                        actual_qty=actual_qty,
                        consensus_qty=round(forecast_qty * 1.01, 0),
                        confidence=85.0,
                        status="approved",
                        created_by=planner.id if planner else None,
                    )
                    db.add(plan)
            # Current month (draft)
            current_period = today.replace(day=1)
            existing = db.query(DemandPlan).filter(
                DemandPlan.product_id == product.id,
                DemandPlan.period == current_period,
            ).first()
            if not existing:
                plan = DemandPlan(
                    product_id=product.id,
                    period=current_period,
                    forecast_qty=round(base_demand * random.uniform(0.95, 1.05), 0),
                    status="draft",
                    created_by=planner.id if planner else None,
                )
                db.add(plan)
        db.commit()
        print("✅ Demand plans seeded")

        # ── Supply Plans ──────────────────────────────────────────────────────
        supply_planner = created_users.get("supply_planner")
        for product, base_demand in zip(created_products, base_demands):
            for months_ago in range(6, 0, -1):
                period = (today - relativedelta(months=months_ago)).replace(day=1)
                capacity = round(base_demand * 1.3, 0)
                planned = round(base_demand * random.uniform(0.95, 1.05), 0)
                existing = db.query(SupplyPlan).filter(
                    SupplyPlan.product_id == product.id,
                    SupplyPlan.period == period,
                ).first()
                if not existing:
                    sp = SupplyPlan(
                        product_id=product.id,
                        period=period,
                        planned_prod_qty=planned,
                        actual_prod_qty=round(planned * random.uniform(0.9, 1.0), 0),
                        capacity_max=capacity,
                        capacity_used=round(planned / capacity * 100, 1),
                        supplier_name=f"Supplier {random.choice(['Alpha', 'Beta', 'Gamma'])}",
                        lead_time_days=product.lead_time_days,
                        cost_per_unit=float(product.unit_cost),
                        status="approved",
                        created_by=supply_planner.id if supply_planner else None,
                    )
                    db.add(sp)
        db.commit()
        print("✅ Supply plans seeded")

        # ── Inventory ─────────────────────────────────────────────────────────
        inv_manager = created_users.get("inventory_manager")
        statuses = ["normal", "normal", "normal", "low", "critical", "excess", "normal"]
        for product, base_demand, status in zip(created_products, base_demands, statuses):
            existing = db.query(Inventory).filter(
                Inventory.product_id == product.id,
                Inventory.location == "Main Warehouse",
            ).first()
            if not existing:
                safety = round(base_demand * 0.5, 0)
                reorder = round(base_demand * 0.3, 0)
                max_stock = round(base_demand * 2.0, 0)
                if status == "critical":
                    on_hand = round(reorder * 0.5, 0)
                elif status == "low":
                    on_hand = round(safety * 0.7, 0)
                elif status == "excess":
                    on_hand = round(max_stock * 1.3, 0)
                else:
                    on_hand = round(base_demand * random.uniform(0.8, 1.5), 0)
                inv = Inventory(
                    product_id=product.id,
                    location="Main Warehouse",
                    on_hand_qty=on_hand,
                    allocated_qty=round(on_hand * 0.1, 0),
                    in_transit_qty=round(base_demand * 0.2, 0),
                    safety_stock=safety,
                    reorder_point=reorder,
                    max_stock=max_stock,
                    days_of_supply=round(on_hand / (base_demand / 30), 1) if base_demand else 0,
                    valuation=round(on_hand * float(product.unit_cost), 2),
                    status=status,
                )
                db.add(inv)
        db.commit()
        print("✅ Inventory seeded")

        # ── S&OP Cycle ────────────────────────────────────────────────────────
        coordinator = created_users.get("sop_coordinator")
        existing_cycle = db.query(SOPCycle).filter(SOPCycle.overall_status == "active").first()
        if not existing_cycle:
            cycle_period = today.replace(day=1)
            cycle = SOPCycle(
                cycle_name=f"{cycle_period.strftime('%B %Y')} S&OP Cycle",
                period=cycle_period,
                current_step=2,
                step_1_status="completed",
                step_1_due_date=cycle_period + timedelta(days=5),
                step_1_owner_id=coordinator.id if coordinator else None,
                step_2_status="in_progress",
                step_2_due_date=cycle_period + timedelta(days=12),
                step_2_owner_id=planner.id if planner else None,
                step_3_status="pending",
                step_3_due_date=cycle_period + timedelta(days=18),
                step_3_owner_id=supply_planner.id if supply_planner else None,
                step_4_status="pending",
                step_4_due_date=cycle_period + timedelta(days=22),
                step_4_owner_id=coordinator.id if coordinator else None,
                step_5_status="pending",
                step_5_due_date=cycle_period + timedelta(days=25),
                overall_status="active",
                notes="Monthly S&OP cycle - focus on Q2 demand planning",
            )
            db.add(cycle)
            db.commit()
        print("✅ S&OP cycle seeded")

        # ── KPI Metrics ───────────────────────────────────────────────────────
        kpi_data = [
            # Demand KPIs
            {"metric_name": "forecast_accuracy", "metric_category": "demand", "value": 87.3, "target": 90.0, "unit": "%"},
            {"metric_name": "forecast_bias", "metric_category": "demand", "value": 2.1, "target": 5.0, "unit": "%"},
            {"metric_name": "demand_plan_adherence", "metric_category": "demand", "value": 92.5, "target": 90.0, "unit": "%"},
            # Supply KPIs
            {"metric_name": "capacity_utilization", "metric_category": "supply", "value": 78.4, "target": 80.0, "unit": "%"},
            {"metric_name": "production_plan_adherence", "metric_category": "supply", "value": 94.2, "target": 95.0, "unit": "%"},
            {"metric_name": "supplier_otd", "metric_category": "supply", "value": 96.1, "target": 95.0, "unit": "%"},
            # Inventory KPIs
            {"metric_name": "inventory_turns", "metric_category": "inventory", "value": 8.7, "target": 8.0, "unit": "turns"},
            {"metric_name": "days_of_supply", "metric_category": "inventory", "value": 22.4, "target": 25.0, "unit": "days"},
            {"metric_name": "excess_obsolete_pct", "metric_category": "inventory", "value": 3.2, "target": 5.0, "unit": "%"},
            # Service KPIs
            {"metric_name": "otif", "metric_category": "service", "value": 94.2, "target": 95.0, "unit": "%"},
            {"metric_name": "fill_rate", "metric_category": "service", "value": 97.8, "target": 98.0, "unit": "%"},
            # Financial KPIs
            {"metric_name": "revenue_vs_plan", "metric_category": "financial", "value": 98.5, "target": 100.0, "unit": "%"},
            {"metric_name": "gross_margin", "metric_category": "financial", "value": 32.4, "target": 30.0, "unit": "%"},
        ]
        current_period = today.replace(day=1)
        for kpi in kpi_data:
            existing = db.query(KPIMetric).filter(
                KPIMetric.metric_name == kpi["metric_name"],
                KPIMetric.period == current_period,
            ).first()
            if not existing:
                from decimal import Decimal
                val = Decimal(str(kpi["value"]))
                tgt = Decimal(str(kpi["target"]))
                variance = val - tgt
                variance_pct = (variance / tgt * 100) if tgt else None
                metric = KPIMetric(
                    metric_name=kpi["metric_name"],
                    metric_category=kpi["metric_category"],
                    period=current_period,
                    value=val,
                    target=tgt,
                    previous_value=Decimal(str(round(kpi["value"] * random.uniform(0.95, 1.05), 1))),
                    variance=variance,
                    variance_pct=variance_pct,
                    trend="improving" if variance > 0 else "declining",
                    unit=kpi["unit"],
                )
                db.add(metric)
        db.commit()
        print("✅ KPI metrics seeded")

        print("\n🎉 Seed data complete!")
        print("\n📋 Default Login Credentials:")
        print("  Admin:       admin@genxsop.com / Password123!")
        print("  Executive:   executive@genxsop.com / Password123!")
        print("  Demand:      demand@genxsop.com / Password123!")
        print("  Supply:      supply@genxsop.com / Password123!")
        print("  Inventory:   inventory@genxsop.com / Password123!")
        print("  Finance:     finance@genxsop.com / Password123!")
        print("  Coordinator: coordinator@genxsop.com / Password123!")
        print("  Viewer:      viewer@genxsop.com / Password123!")

    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding data: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()

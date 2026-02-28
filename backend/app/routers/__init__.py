# Routers package — Thin Controllers (SRP / DIP)
from app.routers import (
    auth,
    products,
    demand,
    supply,
    inventory,
    scenarios,
    sop_cycles,
    kpi,
    forecasting,
    dashboard,
    integrations,
    production_scheduling,
)

__all__ = [
    "auth",
    "products",
    "demand",
    "supply",
    "inventory",
    "scenarios",
    "sop_cycles",
    "kpi",
    "forecasting",
    "dashboard",
    "integrations",
    "production_scheduling",
]

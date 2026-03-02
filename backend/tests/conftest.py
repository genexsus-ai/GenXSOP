"""
Shared test fixtures for GenXSOP test suite.

Provides:
- In-memory SQLite database (isolated per test)
- FastAPI TestClient with DB override
- Pre-created admin user + JWT token
- Helper factories for creating test entities
"""
import pytest
from decimal import Decimal
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.models.user import User
from app.models.product import Product, Category
from app.models.demand_plan import DemandPlan
from app.models.supply_plan import SupplyPlan
from app.models.inventory import Inventory
from app.utils.security import get_password_hash, create_access_token

# ── In-memory SQLite engine (isolated per test session) ───────────────────────
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db() -> Session:
    """Provide a clean in-memory DB session for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db: Session) -> TestClient:
    """FastAPI TestClient with DB dependency overridden to use test DB."""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── User / Auth Fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def admin_user(db: Session) -> User:
    """Create and persist an admin user."""
    user = User(
        email="admin@genxsop.com",
        hashed_password=get_password_hash("Admin@123"),
        full_name="Admin User",
        role="admin",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def demand_planner_user(db: Session) -> User:
    user = User(
        email="planner@genxsop.com",
        hashed_password=get_password_hash("Planner@123"),
        full_name="Demand Planner",
        role="demand_planner",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_token(admin_user: User) -> str:
    """JWT token for the admin user."""
    return create_access_token(data={"sub": str(admin_user.id)})


@pytest.fixture
def planner_token(demand_planner_user: User) -> str:
    return create_access_token(data={"sub": str(demand_planner_user.id)})


@pytest.fixture
def admin_headers(admin_token: str) -> dict:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def planner_headers(planner_token: str) -> dict:
    return {"Authorization": f"Bearer {planner_token}"}


# ── Domain Entity Fixtures ────────────────────────────────────────────────────

@pytest.fixture
def category(db: Session) -> Category:
    cat = Category(name="Electronics", description="Electronic products")
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@pytest.fixture
def product(db: Session, category: Category) -> Product:
    p = Product(
        sku="SKU-001",
        name="Test Product",
        category_id=category.id,
        unit_cost=Decimal("100.00"),
        selling_price=Decimal("150.00"),
        lead_time_days=14,
        status="active",
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@pytest.fixture
def demand_plan(db: Session, product: Product, admin_user: User) -> DemandPlan:
    plan = DemandPlan(
        product_id=product.id,
        period=date(2026, 3, 1),
        forecast_qty=Decimal("500.00"),
        status="draft",
        created_by=admin_user.id,
        version=1,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@pytest.fixture
def supply_plan(db: Session, product: Product, admin_user: User) -> SupplyPlan:
    plan = SupplyPlan(
        product_id=product.id,
        period=date(2026, 3, 1),
        planned_prod_qty=Decimal("480.00"),
        status="draft",
        created_by=admin_user.id,
        version=1,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@pytest.fixture
def inventory(db: Session, product: Product) -> Inventory:
    inv = Inventory(
        product_id=product.id,
        location="Warehouse A",
        on_hand_qty=Decimal("200.00"),
        safety_stock=Decimal("50.00"),
        reorder_point=Decimal("80.00"),
        max_stock=Decimal("600.00"),
        status="normal",
        valuation=Decimal("20000.00"),
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return inv

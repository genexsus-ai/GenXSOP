"""
GenXSOP FastAPI Application Entry Point

Architecture patterns applied:
- Global exception handlers (convert domain exceptions → HTTP responses)
- Observer Pattern: EventBus initialized at startup with AuditLogHandler
- Dependency Inversion: All routers depend on service abstractions
"""
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import create_tables, SessionLocal
from app.core.exceptions import GenXSOPException, to_http_exception
from app.utils.events import configure_event_bus
from app.routers import auth, products, demand, supply, inventory, scenarios, sop_cycles, kpi, forecasting, dashboard

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Next-Generation Sales & Operations Planning Platform — Built with SOLID, GoF Design Patterns",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS Middleware ───────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global Exception Handlers ─────────────────────────────────────────────────

@app.exception_handler(GenXSOPException)
async def genxsop_exception_handler(request: Request, exc: GenXSOPException) -> JSONResponse:
    """
    Converts all domain exceptions to structured HTTP responses.
    Keeps routers clean — they never need to catch domain exceptions.
    """
    http_exc = to_http_exception(exc)
    return JSONResponse(
        status_code=http_exc.status_code,
        content={"success": False, "error": http_exc.detail},
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"success": False, "error": {"code": "VALIDATION_ERROR", "message": str(exc)}},
    )


# ── API Routers ───────────────────────────────────────────────────────────────
API_PREFIX = "/api/v1"
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(dashboard.router, prefix=API_PREFIX)
app.include_router(products.router, prefix=API_PREFIX)
app.include_router(demand.router, prefix=API_PREFIX)
app.include_router(supply.router, prefix=API_PREFIX)
app.include_router(inventory.router, prefix=API_PREFIX)
app.include_router(forecasting.router, prefix=API_PREFIX)
app.include_router(scenarios.router, prefix=API_PREFIX)
app.include_router(sop_cycles.router, prefix=API_PREFIX)
app.include_router(kpi.router, prefix=API_PREFIX)


# ── Lifecycle Events ──────────────────────────────────────────────────────────

@app.on_event("startup")
def startup_event():
    """
    Application startup:
    1. Create database tables
    2. Initialize EventBus with AuditLogHandler (Observer Pattern)
    """
    logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)
    create_tables()
    # Configure Observer Pattern: EventBus with AuditLog + Logging handlers
    configure_event_bus(db_session_factory=SessionLocal)
    logger.info("EventBus initialized with AuditLogHandler and LoggingHandler")
    logger.info("API available at http://localhost:8000/docs")


@app.on_event("shutdown")
def shutdown_event():
    logger.info("%s shutting down.", settings.APP_NAME)


# ── Health Endpoints ──────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "status": "running",
        "architecture": {
            "patterns": [
                "Repository Pattern (GoF) — data access layer",
                "Service Layer (SRP/DIP) — business logic",
                "Strategy Pattern (GoF) — ML forecasting models",
                "Factory Pattern (GoF) — model creation",
                "Observer Pattern (GoF) — audit logging via EventBus",
                "Thin Controllers — routers delegate to services",
            ]
        },
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy", "app": settings.APP_NAME}

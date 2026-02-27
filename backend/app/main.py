"""
GenXSOP FastAPI Application Entry Point

Architecture patterns applied:
- Global exception handlers (convert domain exceptions → HTTP responses)
- Observer Pattern: EventBus initialized at startup with AuditLogHandler
- Dependency Inversion: All routers depend on service abstractions
"""
import logging
import time
import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import settings
from app.database import create_tables, SessionLocal, engine
from app.core.exceptions import GenXSOPException, to_http_exception
from app.utils.events import configure_event_bus
from app.utils.logging import configure_logging
from app.routers import auth, products, demand, supply, inventory, scenarios, sop_cycles, kpi, forecasting, dashboard

configure_logging(log_level=settings.LOG_LEVEL, log_format=settings.LOG_FORMAT)
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


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    """
    Adds request correlation metadata for observability.
    - Reads incoming X-Request-ID (if present) or generates one
    - Exposes request_id on request.state for handlers/endpoints
    - Adds timing header for basic performance visibility
    """
    start = time.perf_counter()
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id

    response = await call_next(request)

    duration_ms = (time.perf_counter() - start) * 1000
    if settings.ENABLE_REQUEST_ID:
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}"

    if settings.ENABLE_REQUEST_LOGGING:
        logger.info(
            "request_completed method=%s path=%s status=%s duration_ms=%.2f request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request_id,
        )

    if settings.ENABLE_SECURITY_HEADERS:
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        if not settings.DEBUG:
            response.headers["Strict-Transport-Security"] = (
                f"max-age={settings.STRICT_TRANSPORT_SECURITY_SECONDS}; includeSubDomains"
            )

    return response

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


@app.get("/ready", tags=["Health"])
def readiness_check(request: Request):
    """
    Lightweight readiness endpoint intended for orchestrators.
    """
    db_ok = True
    db_error = None

    if settings.READINESS_CHECK_DATABASE:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception as exc:
            db_ok = False
            db_error = str(exc)

    status = "ready" if db_ok else "not_ready"
    status_code = 200 if db_ok else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": status,
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "request_id": getattr(request.state, "request_id", None),
            "checks": {
                "database": {
                    "enabled": settings.READINESS_CHECK_DATABASE,
                    "ok": db_ok,
                    "error": db_error,
                }
            },
        },
    )

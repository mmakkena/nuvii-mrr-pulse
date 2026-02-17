import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db

logger = logging.getLogger(__name__)

if settings.otel_enabled:
    try:
        from app.telemetry import setup_telemetry
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        setup_telemetry(settings.otel_service_name, settings.otel_endpoint)
    except Exception:
        logger.exception("OpenTelemetry setup failed — continuing without tracing")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup - initialize database tables
    print("Initializing database...")
    await init_db()
    print("Database initialized successfully!")
    yield
    # Shutdown
    print("Shutting down...")


app = FastAPI(
    title="MRRPulse API",
    description="Stripe-first alerting and early-warning system for SaaS founders",
    version="1.0.0",
    lifespan=lifespan,
)

if settings.otel_enabled:
    try:
        FastAPIInstrumentor.instrument_app(app)
    except Exception:
        logger.exception("FastAPIInstrumentor setup failed — continuing without tracing")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}


# Import and include routers
from app.api import auth, workspaces, stripe_connect, webhooks, alerts, rules, integrations, risk, billing, dashboard, admin, metrics

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(workspaces.router, prefix="/api/workspaces", tags=["Workspaces"])
app.include_router(stripe_connect.router, prefix="/api/stripe", tags=["Stripe Connect"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["Webhooks"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["Alerts"])
app.include_router(rules.router, prefix="/api/rules", tags=["Alert Rules"])
app.include_router(integrations.router, prefix="/api/integrations", tags=["Integrations"])
app.include_router(risk.router, prefix="/api/risk", tags=["Risk"])
app.include_router(billing.router, prefix="/api/billing", tags=["Billing"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(metrics.router, prefix="/api/metrics", tags=["Metrics"])

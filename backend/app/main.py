from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db


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
from app.api import auth, workspaces, stripe_connect, webhooks, alerts, rules, integrations, risk, billing

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(workspaces.router, prefix="/api/workspaces", tags=["Workspaces"])
app.include_router(stripe_connect.router, prefix="/api/stripe", tags=["Stripe Connect"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["Webhooks"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["Alerts"])
app.include_router(rules.router, prefix="/api/rules", tags=["Alert Rules"])
app.include_router(integrations.router, prefix="/api/integrations", tags=["Integrations"])
app.include_router(risk.router, prefix="/api/risk", tags=["Risk"])
app.include_router(billing.router, prefix="/api/billing", tags=["Billing"])

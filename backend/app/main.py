"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.routers import auth, subscriptions, decisions
from app.routers.enterprise import (
    organizations_router,
    users_router,
    tools_router,
    subscriptions_router as enterprise_subscriptions_router,
    decisions_router as enterprise_decisions_router,
    integrations_router,
    dashboard_router,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    await init_db()
    yield
    # Shutdown
    pass


app = FastAPI(
    title="Sub-Zero API",
    description="Subscription management and optimization API",
    version="0.1.0",
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

# Include routers - Individual Product
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(subscriptions.router, prefix="/subscriptions", tags=["Subscriptions"])
app.include_router(decisions.router, prefix="/decisions", tags=["Decisions"])

# Include routers - Enterprise Platform
app.include_router(organizations_router, prefix="/api/v1", tags=["Organizations"])
app.include_router(users_router, prefix="/api/v1", tags=["Organization Users"])
app.include_router(tools_router, prefix="/api/v1", tags=["SaaS Tools"])
app.include_router(enterprise_subscriptions_router, prefix="/api/v1", tags=["Enterprise Subscriptions"])
app.include_router(enterprise_decisions_router, prefix="/api/v1", tags=["Enterprise Decisions"])
app.include_router(integrations_router, prefix="/api/v1", tags=["Integrations"])
app.include_router(dashboard_router, prefix="/api/v1", tags=["Dashboard"])


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "healthy", "service": "sub-zero"}


@app.get("/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "service": "sub-zero",
    }

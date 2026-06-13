"""NetInsight API – main FastAPI application."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1 import auth, campaigns, dashboard, hosts, reports, sqlmap, vulnerabilities, admin_users, mitre, audit, banners, nikto
from app.core.config import get_settings
from app.core.db import init_db
from app.core.limiter import limiter

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialise DB connection on startup."""
    await init_db()
    # Preload MITRE dataset in background
    import asyncio as _asyncio
    _asyncio.create_task(_preload_mitre())
    yield


async def _preload_mitre():
    """Preload MITRE ATT&CK dataset in background."""
    try:
        from app.services.mitre_service import load_mitre_enterprise
        dataset = await load_mitre_enterprise()
        logger = logging.getLogger("uvicorn")
        logger.info("MITRE ATT&CK dataset loaded: %d techniques", len(dataset.get("by_id", {})))
    except Exception as e:
        logging.getLogger("uvicorn").warning("MITRE preload failed: %s", e)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(campaigns.router, prefix="/api/v1")
app.include_router(hosts.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(vulnerabilities.router, prefix="/api/v1")
app.include_router(sqlmap.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(admin_users.router, prefix="/api/v1")
app.include_router(mitre.router, prefix="/api/v1")
app.include_router(audit.router, prefix="/api/v1")
app.include_router(banners.router, prefix="/api/v1")
app.include_router(nikto.router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health-check endpoint."""
    return {"status": "ok", "version": settings.APP_VERSION}

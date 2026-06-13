"""
Celery application for NetInsight background tasks.

Usage:
    celery -A app.tasks worker --loglevel=info
    celery -A app.tasks beat --loglevel=info
"""

import asyncio
import logging
from typing import Optional

from celery import Celery
from celery.signals import worker_process_init

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# ---------------------------------------------------------------------------
# Celery app
# ---------------------------------------------------------------------------
celery_app = Celery(
    "netinsight",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# ---------------------------------------------------------------------------
# Per-worker-process async utilities
# ---------------------------------------------------------------------------
_worker_loop: Optional[asyncio.AbstractEventLoop] = None
_db_initialized: bool = False


def get_worker_loop() -> asyncio.AbstractEventLoop:
    """Return (or create) the persistent event loop for this worker process."""
    global _worker_loop
    if _worker_loop is None or _worker_loop.is_closed():
        _worker_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_worker_loop)
    return _worker_loop


def ensure_db_initialized() -> None:
    """Initialise Beanie / MongoDB for this worker process (idempotent)."""
    global _db_initialized
    if _db_initialized:
        return

    from app.core.db import init_db

    loop = get_worker_loop()
    try:
        loop.run_until_complete(init_db())
        _db_initialized = True
        logger.info("Database initialised for Celery worker process")
    except Exception:
        logger.exception("Failed to initialise database for Celery worker")


@worker_process_init.connect
def _on_worker_process_init(**kwargs: object) -> None:
    """Celery signal: called once when each worker child-process starts."""
    ensure_db_initialized()


# ---------------------------------------------------------------------------
# Task auto-discovery
# ---------------------------------------------------------------------------
# Must run after celery_app is defined and DB helpers are ready.
# Discovers @celery_app.task decorators in submodules.
celery_app.autodiscover_tasks(["app.tasks.scans", "app.tasks.reports", "app.tasks.sqlmap", "app.tasks.banners", "app.tasks.nikto"])

"""FastAPI application entry point.

Workflow logic moved to Celery workers (see app/tasks/ and app/celery_app.py).
This file only handles HTTP API.
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.api.v1 import api_router
from app.core.rate_limit import limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.db.session import engine
from app.models import *  # noqa: F403 — register all models with Base


# ==================== Logging ====================
setup_logging(level="INFO", structured=settings.DEBUG is False)
logger = logging.getLogger(__name__)


# ==================== App lifecycle ====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info("Workflow engine: Celery (see celery worker + beat services)")

    # Register event handlers (importing the module triggers @event_bus.on decorators)
    from app.events import handlers
    handlers.register_all()

    # Optional Sentry
    try:
        import os
        if os.getenv("SENTRY_DSN"):
            import sentry_sdk
            from sentry_sdk.integrations.fastapi import FastApiIntegration
            sentry_sdk.init(
                dsn=os.getenv("SENTRY_DSN"),
                integrations=[FastApiIntegration()],
                traces_sample_rate=0.1,
                environment=os.getenv("ENVIRONMENT", "production"),
            )
            logger.info("Sentry initialized")
    except ImportError:
        logger.debug("sentry-sdk not installed")
    except Exception as e:
        logger.warning(f"Sentry init failed: {e}")

    yield
    await engine.dispose()
    logger.info("Application shutdown complete")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.APP_VERSION}

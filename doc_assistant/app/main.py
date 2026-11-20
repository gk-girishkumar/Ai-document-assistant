"""FastAPI main application entrypoint."""

from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from doc_assistant.app.api.auth import router as auth_router
from doc_assistant.app.api.chat import router as chat_router
from doc_assistant.app.api.documents import router as documents_router
from doc_assistant.app.api.users import router as users_router
from doc_assistant.app.core.config import settings
from doc_assistant.app.core.database import engine

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("doc_assistant")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context for startup and shutdown routines."""
    # Ensure upload directory exists on startup
    upload_path = Path(settings.UPLOAD_DIR)
    upload_path.mkdir(parents=True, exist_ok=True)
    logger.info("Upload directory initialized at: %s", upload_path.resolve())
    yield
    # Cleanup database pool on shutdown
    if engine is not None:
        await engine.dispose()
    logger.info("Application shutdown complete.")


app = FastAPI(
    title="AI Document Assistant API",
    description="Production-grade AI Document Assistant with RAG, pgvector semantic search, and citations.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS Middleware ───────────────────────────────────────────────────────────
origins = settings.CORS_ORIGINS or ["http://localhost:3000", "http://127.0.0.1:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Audit & Timing Middleware ──────────────────────────────────────────────────
@app.middleware("http")
async def audit_and_timing_middleware(request: Request, call_next):
    start_time = time.time()
    path = request.url.path
    method = request.method

    response = await call_next(request)
    duration = time.time() - start_time

    # Never log sensitive payloads or Authorization headers
    if path.startswith("/api/"):
        logger.info(
            "%s %s -> status %d (%.2fms)",
            method,
            path,
            response.status_code,
            duration * 1000,
        )
    return response


# ── Global Safe Exception Handler ──────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch unhandled exceptions and return safe JSON response without stack traces."""
    logger.error("Unhandled error processing %s: %s", request.url.path, str(exc), exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please try again later."},
    )


# ── Health & Readiness Endpoints ──────────────────────────────────────────────
@app.get("/health", summary="Health check endpoint", tags=["System"])
async def health_check():
    """Liveness probe returning 200 when service process is running."""
    return {"status": "healthy"}


@app.get("/ready", summary="Readiness probe checking database & redis", tags=["System"])
async def readiness_check():
    """Readiness probe checking database and redis dependencies."""
    db_ok = False
    redis_ok = False

    # Check Database connectivity
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            db_ok = True
    except Exception as e:
        logger.warning("Readiness probe database check failed: %s", e)

    # Check Redis connectivity
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.close()
        redis_ok = True
    except Exception as e:
        logger.warning("Readiness probe Redis check failed: %s", e)

    is_ready = db_ok  # Service can serve basic requests even if cache warming
    status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if is_ready else "not_ready",
            "database": db_ok,
            "redis": redis_ok,
        },
    )


# ── Include API Routers ────────────────────────────────────────────────────────
app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(documents_router, prefix="/api")
app.include_router(chat_router, prefix="/api")

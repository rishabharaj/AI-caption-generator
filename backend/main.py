"""
CapturaAI — FastAPI application entry point.

Creates the FastAPI app with CORS middleware, mounts static files for the
frontend, includes API routes, and manages startup/shutdown lifecycle events.
"""

import logging
import sys
import asyncio
import time

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.api.exceptions import register_exception_handlers
from backend.api.routes import router as api_router
from backend.config import settings
from backend.utils.file_utils import cleanup_all_temp, ensure_temp_directory

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle.

    Startup: create temp directories.
    Shutdown: optionally clean up temp files.
    """
    # --- STARTUP ---
    start_time = time.monotonic()
    logger.info("=" * 60)
    logger.info("  CapturaAI v%s starting up", settings.app_version)
    logger.info("=" * 60)

    temp_path = ensure_temp_directory()
    logger.info("Temp directory ready: %s", temp_path)

    # Ensure frontend directory exists (for static mount)
    frontend_path = settings.frontend_path
    if not frontend_path.exists():
        frontend_path.mkdir(parents=True, exist_ok=True)
        logger.warning("Frontend directory created (empty): %s", frontend_path)

    elapsed = time.monotonic() - start_time
    logger.info("Server ready in %.2fs on http://%s:%d", elapsed, settings.server.host, settings.server.port)
    logger.info("API docs available at http://%s:%d/docs", settings.server.host, settings.server.port)

    yield  # Application is running

    # --- SHUTDOWN ---
    logger.info("CapturaAI shutting down...")
    if settings.debug:
        count = cleanup_all_temp()
        logger.info("Cleaned up %d temp directories", count)
    logger.info("Goodbye!")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "CapturaAI — 4-Style Video Captioning Platform. "
        "Upload a video, generate 4 caption styles (Formal, Sarcastic, "
        "Humorous-Tech, Humorous-NonTech), and export with burned subtitles."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS Middleware (allow all origins for development)
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

# ---------------------------------------------------------------------------
# Register custom exception handlers
# ---------------------------------------------------------------------------
register_exception_handlers(app)

# ---------------------------------------------------------------------------
# Include API router
# ---------------------------------------------------------------------------
app.include_router(api_router)


# ---------------------------------------------------------------------------
# Ultra-fast health check — NO heavy imports, NO network calls
# This is the FIRST thing automation tests hit; it must respond < 100ms
# ---------------------------------------------------------------------------
@app.get("/health", include_in_schema=False)
async def health_check():
    """Lightweight health check endpoint for automation/Docker HEALTHCHECK."""
    return JSONResponse(
        content={
            "status": "healthy",
            "app": settings.app_name,
            "version": settings.app_version,
        },
        status_code=200,
    )


# ---------------------------------------------------------------------------
# Detailed health check (for debugging, not automation-critical)
# ---------------------------------------------------------------------------
@app.get("/health/detailed", include_in_schema=False)
async def health_check_detailed():
    """Detailed health check with dependency status — use for debugging."""
    from backend.utils.ffmpeg_utils import is_ffmpeg_available, is_ffprobe_available
    from backend.services.whisper_client import WhisperClient
    whisper_client = WhisperClient()
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
        "ffmpeg_available": is_ffmpeg_available(),
        "ffprobe_available": is_ffprobe_available(),
        "whisper_available": whisper_client.is_available(),
        "whisper_model": settings.whisper.model_name,
        "stt_mode": "local_whisper",
    }


# ---------------------------------------------------------------------------
# Root endpoint — fast JSON response (works even if frontend dir is missing)
# ---------------------------------------------------------------------------
@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint returns app info. Useful for automation to verify the app is running."""
    return JSONResponse(
        content={
            "app": settings.app_name,
            "version": settings.app_version,
            "status": "running",
            "docs": "/docs",
            "health": "/health",
            "api_prefix": "/api",
        },
        status_code=200,
    )


# ---------------------------------------------------------------------------
# Mount static files for frontend (AFTER root endpoint so / JSON always works)
# ---------------------------------------------------------------------------
frontend_dir = settings.frontend_path
if frontend_dir.exists():
    # Mount at /app to avoid overriding root
    app.mount(
        "/app",
        StaticFiles(directory=str(frontend_dir), html=True),
        name="static",
    )
    logger.info("Frontend static files mounted at /app from %s", frontend_dir)


# ---------------------------------------------------------------------------
# Uvicorn entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.server.host,
        port=settings.server.port,
        reload=settings.server.reload,
        workers=settings.server.workers,
        log_level="debug" if settings.debug else "info",
    )

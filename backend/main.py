"""
CapturaAI — FastAPI application entry point.

Creates the FastAPI app with CORS middleware, mounts static files for the
frontend, includes API routes, and manages startup/shutdown lifecycle events.
"""

import logging
import sys
import asyncio
import sys

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

    logger.info("Server running on http://%s:%d", settings.server.host, settings.server.port)
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

@app.get("/health", include_in_schema=False)
async def health_check():
    """Health check endpoint."""
    from backend.utils.ffmpeg_utils import is_ffmpeg_available, is_ffprobe_available
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
        "ffmpeg_available": is_ffmpeg_available(),
        "ffprobe_available": is_ffprobe_available(),
    }


# ---------------------------------------------------------------------------
# Mount static files for frontend at root
# ---------------------------------------------------------------------------
frontend_dir = settings.frontend_path
if frontend_dir.exists():
    app.mount(
        "/",
        StaticFiles(directory=str(frontend_dir), html=True),
        name="static",
    )
    logger.info("Frontend static files mounted at root / from %s", frontend_dir)
else:
    @app.get("/", include_in_schema=False)
    async def serve_frontend_fallback():
        return JSONResponse(
            content={
                "app": settings.app_name,
                "version": settings.app_version,
                "docs": "/docs",
                "message": "Frontend not found. Place files in the frontend/ directory.",
            }
        )



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

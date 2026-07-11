"""
CapturaAI — Custom exception classes and FastAPI exception handlers.
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom Exception Classes
# ---------------------------------------------------------------------------

class CapturaAIError(Exception):
    """Base exception for all CapturaAI errors."""

    def __init__(self, message: str, status_code: int = 500, details: Any = None):
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)


class VideoTooShort(CapturaAIError):
    """Raised when a video is shorter than the minimum duration (30s)."""

    def __init__(self, duration: float, min_duration: float = 30.0):
        super().__init__(
            message=f"Video is too short ({duration:.1f}s). Minimum duration is {min_duration:.0f}s.",
            status_code=422,
            details={"duration": duration, "min_duration": min_duration},
        )


class VideoTooLong(CapturaAIError):
    """Raised when a video exceeds the maximum duration (2 minutes)."""

    def __init__(self, duration: float, max_duration: float = 120.0):
        super().__init__(
            message=f"Video is too long ({duration:.1f}s). Maximum duration is {max_duration:.0f}s.",
            status_code=422,
            details={"duration": duration, "max_duration": max_duration},
        )


class FileTooLarge(CapturaAIError):
    """Raised when a file exceeds the maximum size (500MB)."""

    def __init__(self, size_bytes: int, max_size_mb: int = 500):
        size_mb = size_bytes / (1024 * 1024)
        super().__init__(
            message=f"File is too large ({size_mb:.1f}MB). Maximum size is {max_size_mb}MB.",
            status_code=413,
            details={"file_size_mb": round(size_mb, 1), "max_size_mb": max_size_mb},
        )


class InvalidFormat(CapturaAIError):
    """Raised when the uploaded file format is not supported."""

    def __init__(self, format_name: str, allowed: list[str] | None = None):
        allowed_str = ", ".join(allowed) if allowed else "MP4, MOV, AVI, WEBM"
        super().__init__(
            message=f"Invalid file format: .{format_name}. Allowed formats: {allowed_str}",
            status_code=415,
            details={"format": format_name, "allowed_formats": allowed or []},
        )


class ProcessingError(CapturaAIError):
    """Raised when video processing fails."""

    def __init__(self, message: str, step: str = "unknown"):
        super().__init__(
            message=f"Processing error at step '{step}': {message}",
            status_code=500,
            details={"step": step},
        )


class APIKeyError(CapturaAIError):
    """Raised when the API key is invalid or missing."""

    def __init__(self, message: str = "Invalid or missing Fireworks API key"):
        super().__init__(
            message=message,
            status_code=401,
            details={"hint": "API key should start with 'fw_' and be at least 32 characters"},
        )


class VideoNotFound(CapturaAIError):
    """Raised when a requested video is not found."""

    def __init__(self, video_id: str):
        super().__init__(
            message=f"Video not found: {video_id}",
            status_code=404,
            details={"video_id": video_id},
        )


class CaptionNotFound(CapturaAIError):
    """Raised when a requested caption is not found."""

    def __init__(self, video_id: str, style: str):
        super().__init__(
            message=f"Caption not found for video {video_id}, style '{style}'",
            status_code=404,
            details={"video_id": video_id, "style": style},
        )


# ---------------------------------------------------------------------------
# Exception Handlers
# ---------------------------------------------------------------------------

def _build_error_response(exc: CapturaAIError) -> JSONResponse:
    """Build a standardized JSON error response."""
    body = {
        "error": True,
        "message": exc.message,
        "status_code": exc.status_code,
    }
    if exc.details:
        body["details"] = exc.details
    return JSONResponse(status_code=exc.status_code, content=body)


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register all custom exception handlers on the FastAPI application.

    Args:
        app: The FastAPI application instance.
    """

    @app.exception_handler(CapturaAIError)
    async def capturaai_error_handler(request: Request, exc: CapturaAIError) -> JSONResponse:
        logger.error("CapturaAI error: %s", exc.message)
        return _build_error_response(exc)

    @app.exception_handler(VideoTooShort)
    async def video_too_short_handler(request: Request, exc: VideoTooShort) -> JSONResponse:
        logger.warning("Video too short: %s", exc.message)
        return _build_error_response(exc)

    @app.exception_handler(VideoTooLong)
    async def video_too_long_handler(request: Request, exc: VideoTooLong) -> JSONResponse:
        logger.warning("Video too long: %s", exc.message)
        return _build_error_response(exc)

    @app.exception_handler(FileTooLarge)
    async def file_too_large_handler(request: Request, exc: FileTooLarge) -> JSONResponse:
        logger.warning("File too large: %s", exc.message)
        return _build_error_response(exc)

    @app.exception_handler(InvalidFormat)
    async def invalid_format_handler(request: Request, exc: InvalidFormat) -> JSONResponse:
        logger.warning("Invalid format: %s", exc.message)
        return _build_error_response(exc)

    @app.exception_handler(ProcessingError)
    async def processing_error_handler(request: Request, exc: ProcessingError) -> JSONResponse:
        logger.error("Processing error: %s", exc.message)
        return _build_error_response(exc)

    @app.exception_handler(APIKeyError)
    async def api_key_error_handler(request: Request, exc: APIKeyError) -> JSONResponse:
        logger.warning("API key error: %s", exc.message)
        return _build_error_response(exc)

    @app.exception_handler(VideoNotFound)
    async def video_not_found_handler(request: Request, exc: VideoNotFound) -> JSONResponse:
        logger.warning("Video not found: %s", exc.message)
        return _build_error_response(exc)

    @app.exception_handler(CaptionNotFound)
    async def caption_not_found_handler(request: Request, exc: CaptionNotFound) -> JSONResponse:
        logger.warning("Caption not found: %s", exc.message)
        return _build_error_response(exc)

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error: %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "message": "An unexpected error occurred. Please try again.",
                "status_code": 500,
            },
        )

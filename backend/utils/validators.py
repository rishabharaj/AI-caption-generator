"""
CapturaAI — Validation utilities.

Validates video duration, file size, file format, and API key format.
"""

import logging
from pathlib import Path

from backend.config import settings

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS: set[str] = {
    ext.lstrip(".").lower() for ext in settings.video.allowed_formats
}


MAX_FILE_SIZE_BYTES: int = settings.video.max_file_size_mb * 1024 * 1024
MIN_DURATION: float = settings.video.min_duration_seconds
MAX_DURATION: float = settings.video.max_duration_seconds


def validate_file_format(filename: str) -> bool:
    """
    Validate that the file extension is one of the allowed video formats.

    Args:
        filename: The original filename (e.g. "clip.mp4").

    Returns:
        True if the format is allowed.
    """
    ext = Path(filename).suffix.lstrip(".").lower()
    is_valid = ext in ALLOWED_EXTENSIONS
    if not is_valid:
        logger.warning(
            "Invalid file format '%s'. Allowed: %s", ext, ALLOWED_EXTENSIONS
        )
    return is_valid


def validate_file_size(size_bytes: int) -> bool:
    """
    Validate that the file size is under the maximum limit.

    Args:
        size_bytes: File size in bytes.

    Returns:
        True if the file is within the size limit.
    """
    is_valid = 0 < size_bytes <= MAX_FILE_SIZE_BYTES
    if not is_valid:
        logger.warning(
            "File size %d bytes exceeds limit of %d bytes (%d MB)",
            size_bytes, MAX_FILE_SIZE_BYTES, settings.video.max_file_size_mb,
        )
    return is_valid


def validate_duration(duration_seconds: float) -> tuple[bool, str]:
    """
    Validate that the video duration falls within the allowed range.

    Args:
        duration_seconds: Video duration in seconds.

    Returns:
        Tuple of (is_valid, error_message). error_message is empty when valid.
    """
    if duration_seconds < MIN_DURATION:
        msg = (
            f"Video is too short ({duration_seconds:.1f}s). "
            f"Minimum duration is {MIN_DURATION:.0f}s."
        )
        logger.warning(msg)
        return False, msg

    if duration_seconds > MAX_DURATION:
        msg = (
            f"Video is too long ({duration_seconds:.1f}s). "
            f"Maximum duration is {MAX_DURATION:.0f}s."
        )
        logger.warning(msg)
        return False, msg

    return True, ""


def validate_api_key(api_key: str) -> bool:
    """
    Validate the Fireworks API key format.

    A valid key starts with 'fw_' and is at least 20 characters long.

    Args:
        api_key: The API key string.

    Returns:
        True if the key format is valid.
    """
    if not api_key:
        return False
    if not api_key.startswith("fw_"):
        logger.warning("API key does not start with 'fw_'")
        return False
    if len(api_key) < 20:
        logger.warning("API key is too short (%d chars, need 20+)", len(api_key))
        return False
    return True


def get_allowed_formats_display() -> str:
    """Return a human-readable string of allowed formats."""
    return ", ".join(sorted(f".{ext.upper()}" for ext in ALLOWED_EXTENSIONS))

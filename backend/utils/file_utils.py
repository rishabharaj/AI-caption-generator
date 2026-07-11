"""
CapturaAI — File utility helpers.

Handles temp directory management, safe file naming, unique video ID generation,
and cleanup utilities.
"""

import logging
import re
import shutil
import uuid
from pathlib import Path

from backend.config import settings

logger = logging.getLogger(__name__)


def generate_video_id() -> str:
    """
    Generate a unique video identifier using UUID4.

    Returns:
        A UUID string (e.g. "a1b2c3d4-e5f6-7890-abcd-ef1234567890").
    """
    return str(uuid.uuid4())


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing unsafe characters.

    Args:
        filename: The original filename.

    Returns:
        A safe filename string.
    """
    # Keep only alphanumeric, hyphens, underscores, dots
    name = re.sub(r"[^\w\-.]", "_", filename)
    # Collapse multiple underscores
    name = re.sub(r"_+", "_", name)
    # Remove leading/trailing underscores and dots
    name = name.strip("_.")
    return name if name else "video"


def get_video_dir(video_id: str) -> Path:
    """
    Get the directory path for a specific video's files.

    Args:
        video_id: The unique video identifier.

    Returns:
        Path to temp/{video_id}/
    """
    return settings.temp_path / video_id


def ensure_video_dir(video_id: str) -> Path:
    """
    Create the directory structure for a video and return the base path.

    Creates subdirectories: frames/, audio/, output/

    Args:
        video_id: The unique video identifier.

    Returns:
        Path to the video's base directory.
    """
    base = get_video_dir(video_id)
    (base / "frames").mkdir(parents=True, exist_ok=True)
    (base / "audio").mkdir(parents=True, exist_ok=True)
    (base / "output").mkdir(parents=True, exist_ok=True)
    (base / "export").mkdir(parents=True, exist_ok=True)
    logger.debug("Ensured directory structure for video %s at %s", video_id, base)
    return base


def get_upload_path(video_id: str, original_filename: str) -> Path:
    """
    Get the path where an uploaded video should be stored.

    Args:
        video_id: The unique video identifier.
        original_filename: The original filename from the upload.

    Returns:
        Full path for the uploaded file.
    """
    safe_name = sanitize_filename(original_filename)
    return get_video_dir(video_id) / safe_name


def get_frames_dir(video_id: str) -> Path:
    """Get the frames directory for a video."""
    return get_video_dir(video_id) / "frames"


def get_audio_dir(video_id: str) -> Path:
    """Get the audio directory for a video."""
    return get_video_dir(video_id) / "audio"


def get_output_dir(video_id: str) -> Path:
    """Get the output directory for styled videos."""
    return get_video_dir(video_id) / "output"


def get_export_dir(video_id: str) -> Path:
    """Get the export directory for generated files."""
    return get_video_dir(video_id) / "export"


def get_styled_video_path(video_id: str, style: str) -> Path:
    """
    Get the output path for a styled video.

    Args:
        video_id: The unique video identifier.
        style: Caption style (e.g. "formal", "sarcastic").

    Returns:
        Path to the styled MP4 file.
    """
    return get_output_dir(video_id) / f"{style}.mp4"


def get_audio_path(video_id: str) -> Path:
    """Get the path for extracted audio."""
    return get_audio_dir(video_id) / "audio.wav"


def cleanup_video(video_id: str) -> bool:
    """
    Remove all files associated with a video.

    Args:
        video_id: The unique video identifier.

    Returns:
        True if cleanup was successful.
    """
    video_dir = get_video_dir(video_id)
    if video_dir.exists():
        try:
            shutil.rmtree(video_dir)
            logger.info("Cleaned up video directory: %s", video_dir)
            return True
        except Exception as exc:
            logger.error("Failed to clean up %s: %s", video_dir, exc)
            return False
    return True


def cleanup_all_temp() -> int:
    """
    Remove all temporary files.

    Returns:
        Number of video directories removed.
    """
    temp = settings.temp_path
    count = 0
    if temp.exists():
        for child in temp.iterdir():
            if child.is_dir():
                try:
                    shutil.rmtree(child)
                    count += 1
                except Exception as exc:
                    logger.error("Failed to remove %s: %s", child, exc)
    logger.info("Cleaned up %d temporary video directories", count)
    return count


def ensure_temp_directory() -> Path:
    """
    Ensure the main temp directory exists.

    Returns:
        Path to the temp directory.
    """
    temp = settings.temp_path
    temp.mkdir(parents=True, exist_ok=True)
    logger.info("Temp directory ready at %s", temp)
    return temp


def find_original_video(video_id: str) -> Path | None:
    """
    Find the original uploaded video file for a given video_id.

    The original file is stored directly in the video directory
    (not in a subdirectory like frames/ or output/).

    Args:
        video_id: The unique video identifier.

    Returns:
        Path to the original video file, or None if not found.
    """
    video_dir = get_video_dir(video_id)
    if not video_dir.exists():
        return None

    video_extensions = {".mp4", ".mov", ".avi", ".webm"}
    for item in video_dir.iterdir():
        if item.is_file() and item.suffix.lower() in video_extensions:
            # Skip files in subdirectories (they are styled outputs)
            return item
    return None

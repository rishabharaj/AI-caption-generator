"""
CapturaAI — FFmpeg utility helpers.

Provides helper functions for building and running ffmpeg/ffprobe commands
with proper error handling. Works on both Windows and Linux.
"""

import asyncio
import json
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Optional

# Add fallback search paths for ffmpeg/ffprobe to system PATH
_fallback_dirs = [
    r"D:\Antigravity\Youtube_bot\ffmpeg\bin",
    r"D:\Antigravity\Video-caption\node_modules\ffmpeg-static",
]
for _dir in _fallback_dirs:
    if os.path.exists(_dir) and _dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = _dir + os.pathsep + os.environ.get("PATH", "")

logger = logging.getLogger(__name__)


def get_ffmpeg_path() -> str:
    """
    Locate the ffmpeg binary on the system.

    Returns:
        Path string to the ffmpeg binary.

    Raises:
        FileNotFoundError: If ffmpeg is not found on the system PATH.
    """
    path = shutil.which("ffmpeg")
    if path is None:
        raise FileNotFoundError(
            "ffmpeg not found on system PATH. "
            "Please install ffmpeg: https://ffmpeg.org/download.html"
        )
    return path


def get_ffprobe_path() -> str:
    """
    Locate the ffprobe binary on the system.

    Returns:
        Path string to the ffprobe binary.

    Raises:
        FileNotFoundError: If ffprobe is not found on the system PATH.
    """
    path = shutil.which("ffprobe")
    if path is None:
        raise FileNotFoundError(
            "ffprobe not found on system PATH. "
            "Please install ffmpeg (includes ffprobe): https://ffmpeg.org/download.html"
        )
    return path


def is_ffmpeg_available() -> bool:
    """
    Check if ffmpeg is available on the system.

    Returns:
        True if ffmpeg is available.
    """
    return shutil.which("ffmpeg") is not None


def is_ffprobe_available() -> bool:
    """
    Check if ffprobe is available on the system.

    Returns:
        True if ffprobe is available.
    """
    return shutil.which("ffprobe") is not None


def _get_subprocess_kwargs() -> dict[str, Any]:
    """Get standard kwargs for subprocess execution including environment and Windows flags."""
    env = os.environ.copy()
    
    # Check if a local fonts.conf exists in the project root to satisfy fontconfig on Heroku
    from backend.config import PROJECT_ROOT
    fonts_conf = PROJECT_ROOT / "fonts.conf"
    if fonts_conf.exists():
        env["FONTCONFIG_FILE"] = str(fonts_conf)
        env["FONTCONFIG_PATH"] = str(PROJECT_ROOT)
        
    kwargs: dict[str, Any] = {"env": env}
    if sys.platform == "win32":
        kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
    return kwargs


async def run_ffmpeg_command(
    args: list[str],
    timeout: int = 300,
    check: bool = True,
) -> tuple[int, str, str]:
    """
    Run an ffmpeg command asynchronously.

    Args:
        args: Command arguments (without the 'ffmpeg' binary itself).
        timeout: Maximum time in seconds to wait for the command.
        check: If True, raise on non-zero exit code.

    Returns:
        Tuple of (return_code, stdout, stderr).

    Raises:
        RuntimeError: If the command fails and check is True.
        asyncio.TimeoutError: If the command exceeds the timeout.
    """
    ffmpeg = get_ffmpeg_path()
    cmd = [ffmpeg] + args

    logger.debug("Running ffmpeg command: %s", " ".join(cmd))

    kwargs = _get_subprocess_kwargs()

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            **kwargs,
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.communicate()
            raise asyncio.TimeoutError(
                f"ffmpeg command timed out after {timeout}s: {' '.join(cmd)}"
            )
        return_code = process.returncode or 0
    except NotImplementedError:
        # Fallback to synchronous subprocess run in a thread executor if event loop doesn't support subprocesses
        import subprocess

        def _run_sync():
            p = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                **kwargs,
            )
            try:
                out, err = p.communicate(timeout=timeout)
                return p.returncode, out, err
            except subprocess.TimeoutExpired:
                p.kill()
                out, err = p.communicate()
                raise asyncio.TimeoutError(
                    f"ffmpeg command timed out after {timeout}s: {' '.join(cmd)}"
                )

        loop = asyncio.get_running_loop()
        return_code, stdout_bytes, stderr_bytes = await loop.run_in_executor(None, _run_sync)

    stdout = stdout_bytes.decode("utf-8", errors="replace")
    stderr = stderr_bytes.decode("utf-8", errors="replace")

    if check and return_code != 0:
        logger.error("ffmpeg failed (code %d): %s", return_code, stderr[:500])
        raise RuntimeError(
            f"ffmpeg command failed with code {return_code}: {stderr[:500]}"
        )

    logger.debug("ffmpeg completed with code %d", return_code)
    return return_code, stdout, stderr


async def run_ffprobe_command(
    args: list[str],
    timeout: int = 30,
) -> tuple[int, str, str]:
    """
    Run an ffprobe command asynchronously.

    Args:
        args: Command arguments (without the 'ffprobe' binary itself).
        timeout: Maximum time in seconds to wait.

    Returns:
        Tuple of (return_code, stdout, stderr).
    """
    ffprobe = get_ffprobe_path()
    cmd = [ffprobe] + args

    logger.debug("Running ffprobe command: %s", " ".join(cmd))

    kwargs = _get_subprocess_kwargs()

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            **kwargs,
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.communicate()
            raise asyncio.TimeoutError(
                f"ffprobe command timed out after {timeout}s"
            )
        return_code = process.returncode or 0
    except NotImplementedError:
        # Fallback to synchronous subprocess run in a thread executor if event loop doesn't support subprocesses
        import subprocess

        def _run_sync():
            p = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                **kwargs,
            )
            try:
                out, err = p.communicate(timeout=timeout)
                return p.returncode, out, err
            except subprocess.TimeoutExpired:
                p.kill()
                out, err = p.communicate()
                raise asyncio.TimeoutError(
                    f"ffprobe command timed out after {timeout}s"
                )

        loop = asyncio.get_running_loop()
        return_code, stdout_bytes, stderr_bytes = await loop.run_in_executor(None, _run_sync)

    stdout = stdout_bytes.decode("utf-8", errors="replace")
    stderr = stderr_bytes.decode("utf-8", errors="replace")

    return return_code, stdout, stderr


async def get_video_info(video_path: Path) -> dict[str, Any]:
    """
    Extract video metadata using ffprobe.

    Args:
        video_path: Path to the video file.

    Returns:
        Dictionary with keys: duration, width, height, fps, has_audio, codec,
        audio_codec, format_name.

    Raises:
        RuntimeError: If ffprobe fails to read the file.
    """
    args = [
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(video_path),
    ]

    return_code, stdout, stderr = await run_ffprobe_command(args)
    if return_code != 0:
        raise RuntimeError(f"ffprobe failed for {video_path}: {stderr[:300]}")

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Failed to parse ffprobe JSON output: {exc}")

    # Extract format info
    fmt = data.get("format", {})
    duration = float(fmt.get("duration", 0))

    # Find video and audio streams
    streams = data.get("streams", [])
    video_stream = next(
        (s for s in streams if s.get("codec_type") == "video"), None
    )
    audio_stream = next(
        (s for s in streams if s.get("codec_type") == "audio"), None
    )

    # Parse FPS from video stream
    fps = 0.0
    if video_stream:
        r_frame_rate = video_stream.get("r_frame_rate", "0/1")
        try:
            num, den = r_frame_rate.split("/")
            fps = float(num) / float(den) if float(den) != 0 else 0.0
        except (ValueError, ZeroDivisionError):
            fps = 0.0

    result = {
        "duration": duration,
        "width": int(video_stream.get("width", 0)) if video_stream else 0,
        "height": int(video_stream.get("height", 0)) if video_stream else 0,
        "fps": round(fps, 2),
        "has_audio": audio_stream is not None,
        "codec": video_stream.get("codec_name", "unknown") if video_stream else "unknown",
        "audio_codec": audio_stream.get("codec_name", "none") if audio_stream else "none",
        "format_name": fmt.get("format_name", "unknown"),
    }

    logger.info(
        "Video info for %s: %dx%d, %.1fs, %.1f fps, audio=%s",
        video_path.name, result["width"], result["height"],
        result["duration"], result["fps"], result["has_audio"],
    )
    return result


def build_drawtext_filter(
    text: str,
    font_file: Optional[str] = None,
    font_size: int = 24,
    font_color: str = "white",
    border_width: int = 2,
    border_color: str = "black",
    video_width: int = 1920,
    video_height: int = 1080,
    enable: Optional[str] = None,
    alpha: Optional[str] = None,
    bottom_padding: Optional[float] = None,
) -> str:
    """
    Build an ffmpeg drawtext filter string for caption burning.

    The text is centered horizontally and positioned at the bottom of the
    video with a semi-transparent background bar for readability.

    Args:
        text: The caption text to burn.
        font_file: Path to the font file (optional; uses system default if None).
        font_size: Font size in pixels.
        font_color: Font color name or hex.
        border_width: Text stroke width.
        border_color: Text stroke color.
        video_width: Video width for text wrapping calculations.
        video_height: Video height for positioning.
        enable: Optional string for timeline enabling (e.g. 'between(t, 2, 5)').
        alpha: Optional string or expression for text opacity.
        bottom_padding: Optional vertical offset percentage from bottom.

    Returns:
        Complete ffmpeg drawtext filter string.
    """
    # Escape special characters for ffmpeg drawtext
    escaped_text = escape_drawtext(text)

    # Build the filter components
    parts = []

    # Font settings
    if font_file:
        safe_path = str(Path(font_file).as_posix()).replace(":", "\\:")
        parts.append(f"fontfile='{safe_path}'")
    parts.append(f"text='{escaped_text}'")
    parts.append(f"fontcolor={font_color}")
    parts.append(f"fontsize={font_size}")
    parts.append(f"borderw={border_width}")
    parts.append(f"bordercolor={border_color}")

    # Background box for readability
    parts.append("box=1")
    parts.append("boxcolor=black@0.5")
    parts.append("boxborderw=8")

    # Center horizontally, position near bottom (using config setting or dynamic override)
    if bottom_padding is None:
        from backend.config import settings
        bottom_padding = settings.caption_burner.bottom_padding_percent
    parts.append("x=(w-text_w)/2")
    parts.append(f"y=h-text_h-h*{bottom_padding:.2f}")

    # Line spacing
    parts.append("line_spacing=4")

    if enable:
        parts.append(f"enable='{enable}'")

    if alpha:
        parts.append(f"alpha='{alpha}'")

    return "drawtext=" + ":".join(parts)


def escape_drawtext(text: str) -> str:
    """
    Escape special characters for ffmpeg drawtext filter.

    Args:
        text: Raw text to escape.

    Returns:
        Escaped text safe for drawtext filter.
    """
    # Escape characters that are special in ffmpeg drawtext
    text = text.replace("\\", "\\\\")
    text = text.replace("'", "'\\\\\\''")
    text = text.replace(":", "\\:")
    text = text.replace("%", "%%")
    text = text.replace("\n", "\\n")
    return text


def wrap_text(text: str, max_chars_per_line: int = 50) -> str:
    """
    Wrap text to fit within video frame width.

    Args:
        text: The caption text.
        max_chars_per_line: Maximum characters per line.

    Returns:
        Text with newline characters inserted for wrapping.
    """
    words = text.split()
    lines: list[str] = []
    current_line: list[str] = []
    current_length = 0

    for word in words:
        if current_length + len(word) + (1 if current_line else 0) > max_chars_per_line:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]
            current_length = len(word)
        else:
            current_line.append(word)
            current_length += len(word) + (1 if len(current_line) > 1 else 0)

    if current_line:
        lines.append(" ".join(current_line))

    return "\n".join(lines)

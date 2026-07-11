"""
CapturaAI — Audio detection service.

Detects whether a video file contains audio streams using ffprobe.
"""

import json
import logging
from pathlib import Path
from typing import Any, Optional

from backend.utils.ffmpeg_utils import run_ffprobe_command

logger = logging.getLogger(__name__)


class AudioStreamInfo:
    """Information about a detected audio stream."""

    def __init__(
        self,
        codec: str = "unknown",
        sample_rate: int = 0,
        channels: int = 0,
        duration: float = 0.0,
        bit_rate: int = 0,
    ):
        self.codec = codec
        self.sample_rate = sample_rate
        self.channels = channels
        self.duration = duration
        self.bit_rate = bit_rate

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "codec": self.codec,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "duration": self.duration,
            "bit_rate": self.bit_rate,
        }

    def __repr__(self) -> str:
        return (
            f"AudioStreamInfo(codec={self.codec!r}, rate={self.sample_rate}, "
            f"channels={self.channels}, duration={self.duration:.1f}s)"
        )


class AudioDetector:
    """
    Detects audio streams in video files using ffprobe.
    """

    async def detect(self, video_path: Path) -> tuple[bool, Optional[AudioStreamInfo]]:
        """
        Detect if the video file has audio streams.

        Args:
            video_path: Path to the video file.

        Returns:
            Tuple of (has_audio, audio_info).
            audio_info is None if no audio stream is found.
        """
        if not video_path.exists():
            logger.error("Video file not found: %s", video_path)
            return False, None

        args = [
            "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            "-select_streams", "a",
            str(video_path),
        ]

        try:
            return_code, stdout, stderr = await run_ffprobe_command(args, timeout=15)
        except Exception as exc:
            logger.error("ffprobe audio detection failed for %s: %s", video_path, exc)
            return False, None

        if return_code != 0:
            logger.warning("ffprobe returned code %d for %s", return_code, video_path)
            return False, None

        try:
            data = json.loads(stdout) if stdout.strip() else {}
        except json.JSONDecodeError:
            logger.warning("Failed to parse ffprobe output for %s", video_path)
            return False, None

        streams = data.get("streams", [])
        if not streams:
            logger.info("No audio streams found in %s", video_path.name)
            return False, None

        # Use the first audio stream
        stream = streams[0]
        info = AudioStreamInfo(
            codec=stream.get("codec_name", "unknown"),
            sample_rate=int(stream.get("sample_rate", 0)),
            channels=int(stream.get("channels", 0)),
            duration=float(stream.get("duration", 0)),
            bit_rate=int(stream.get("bit_rate", 0)) if stream.get("bit_rate") else 0,
        )

        logger.info("Audio stream detected in %s: %s", video_path.name, info)
        return True, info

    async def has_audio(self, video_path: Path) -> bool:
        """
        Simple check: does the video have audio?

        Args:
            video_path: Path to the video file.

        Returns:
            True if the video contains at least one audio stream.
        """
        has_audio, _ = await self.detect(video_path)
        return has_audio

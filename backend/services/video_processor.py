"""
CapturaAI — Video processor service.

Handles frame extraction, audio extraction, and video metadata retrieval
using ffmpeg subprocess calls.
"""

import logging
from pathlib import Path

from backend.config import settings
from backend.utils.ffmpeg_utils import get_video_info, run_ffmpeg_command
from backend.utils.file_utils import get_audio_path, get_frames_dir

logger = logging.getLogger(__name__)


class VideoProcessor:
    """
    Processes uploaded videos: extracts frames, audio, and metadata.
    """

    def __init__(self):
        self.fps = settings.video.frames_per_second
        self.frame_scale_width = settings.video.frame_scale_width
        self.representative_count = settings.video.representative_frames
        self.sample_rate = settings.whisper.sample_rate

    async def get_metadata(self, video_path: Path) -> dict:
        """
        Extract metadata from a video file.

        Args:
            video_path: Path to the video file.

        Returns:
            Dictionary with duration, width, height, fps, has_audio, etc.

        Raises:
            RuntimeError: If metadata extraction fails.
        """
        try:
            info = await get_video_info(video_path)
            logger.info(
                "Extracted metadata for %s: %.1fs, %dx%d, %.1f fps",
                video_path.name, info["duration"], info["width"],
                info["height"], info["fps"],
            )
            return info
        except Exception as exc:
            logger.error("Failed to extract metadata from %s: %s", video_path, exc)
            raise RuntimeError(f"Failed to read video metadata: {exc}") from exc

    async def extract_frames(self, video_path: Path, video_id: str) -> list[Path]:
        """
        Extract frames at 1 FPS and scale them down for analysis.

        Uses ffmpeg: ffmpeg -i input.mp4 -vf "fps=1,scale=480:-1" frames/%04d.jpg

        Args:
            video_path: Path to the source video.
            video_id: Unique identifier for organizing output.

        Returns:
            List of paths to extracted frame images.

        Raises:
            RuntimeError: If frame extraction fails.
        """
        frames_dir = get_frames_dir(video_id)
        frames_dir.mkdir(parents=True, exist_ok=True)

        output_pattern = str(frames_dir / "%04d.jpg")

        args = [
            "-i", str(video_path),
            "-vf", f"fps={self.fps},scale={self.frame_scale_width}:-1",
            "-q:v", "3",  # JPEG quality (2-5, lower is better)
            "-y",  # Overwrite without asking
            output_pattern,
        ]

        try:
            await run_ffmpeg_command(args, timeout=120)
        except Exception as exc:
            logger.error("Frame extraction failed: %s", exc)
            raise RuntimeError(f"Failed to extract frames: {exc}") from exc

        # Collect extracted frames
        frames = sorted(frames_dir.glob("*.jpg"))
        logger.info("Extracted %d frames from %s", len(frames), video_path.name)
        return frames

    async def extract_audio(self, video_path: Path, video_id: str) -> Path:
        """
        Extract audio to WAV format (16kHz, mono) for Whisper transcription.

        Args:
            video_path: Path to the source video.
            video_id: Unique identifier for organizing output.

        Returns:
            Path to the extracted WAV file.

        Raises:
            RuntimeError: If audio extraction fails.
        """
        audio_path = get_audio_path(video_id)
        audio_path.parent.mkdir(parents=True, exist_ok=True)

        args = [
            "-i", str(video_path),
            "-vn",  # Disable video
            "-acodec", "pcm_s16le",  # 16-bit PCM
            "-ar", str(self.sample_rate),  # Sample rate
            "-ac", "1",  # Mono
            "-y",
            str(audio_path),
        ]

        try:
            await run_ffmpeg_command(args, timeout=120)
        except Exception as exc:
            logger.error("Audio extraction failed: %s", exc)
            raise RuntimeError(f"Failed to extract audio: {exc}") from exc

        logger.info(
            "Extracted audio to %s (%.1f KB)",
            audio_path.name, audio_path.stat().st_size / 1024,
        )
        return audio_path

    def select_representative_frames(
        self, frames: list[Path], count: int | None = None,
    ) -> list[Path]:
        """
        Select 5-10 representative frames evenly distributed across the video.

        Args:
            frames: All extracted frames.
            count: Number of frames to select (defaults to config value).

        Returns:
            List of selected frame paths.
        """
        target = count or self.representative_count
        total = len(frames)

        if total == 0:
            logger.warning("No frames available for selection")
            return []

        if total <= target:
            return frames

        # Evenly distribute frame selection
        step = total / target
        selected = []
        for i in range(target):
            idx = int(i * step)
            idx = min(idx, total - 1)
            selected.append(frames[idx])

        logger.info("Selected %d representative frames from %d total", len(selected), total)
        return selected

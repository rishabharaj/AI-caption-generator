"""
CapturaAI — Caption burner service.

Burns captions into video using ffmpeg drawtext filter.
Generates 4 separate MP4 files (one per caption style).
Handles text wrapping and maintains original resolution/frame rate.
"""

import logging
from pathlib import Path
from typing import Optional

from backend.config import settings
from backend.models.caption import CaptionSet, CaptionStyle
from backend.utils.ffmpeg_utils import (
    build_drawtext_filter,
    get_video_info,
    run_ffmpeg_command,
    wrap_text,
)
from backend.utils.file_utils import get_output_dir, get_styled_video_path

logger = logging.getLogger(__name__)


class CaptionBurner:
    """
    Burns caption text into video files using ffmpeg drawtext filter.

    Specs from specification:
    - Font: Inter Bold, 24px
    - Color: white (#ffffff)
    - Stroke: black, 2px
    - Background bar: rgba(0,0,0,0.5) behind text
    - Position: centered, bottom, 10% padding from bottom
    - Line wrapping: max width 90% of video width
    - All outputs maintain original resolution and frame rate
    """

    def __init__(self):
        """Initialize the caption burner with config settings."""
        self.font_file = settings.caption_burner.font_file
        self.font_size = settings.caption_burner.font_size
        self.font_color = settings.caption_burner.font_color
        self.border_width = settings.caption_burner.border_width
        self.border_color = settings.caption_burner.border_color
        self.bg_opacity = settings.caption_burner.background_opacity
        self.bottom_padding = settings.caption_burner.bottom_padding_percent
        self.max_text_width = settings.caption_burner.max_text_width_percent

    async def burn_all_styles(
        self,
        video_path: Path,
        video_id: str,
        caption_set: CaptionSet,
        transcript_segments: Optional[list] = None,
        bottom_padding: Optional[float] = None,
    ) -> dict[str, Path]:
        """
        Burn captions for all 4 styles into separate video files.

        Args:
            video_path: Path to the source video.
            video_id: Unique video identifier.
            caption_set: CaptionSet containing all 4 captions.
            transcript_segments: Optional list of Whisper transcript segments.

        Returns:
            Dictionary mapping style name to output file path.

        Raises:
            RuntimeError: If any burn operation fails.
        """
        output_dir = get_output_dir(video_id)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Get video dimensions for text wrapping
        info = await get_video_info(video_path)
        video_width = info.get("width", 1920)
        video_height = info.get("height", 1080)

        # Calculate max chars per line based on video width and font size
        # Approximate: each char is ~0.6 * font_size pixels wide
        char_width = self.font_size * 0.6
        max_pixel_width = video_width * self.max_text_width
        max_chars = int(max_pixel_width / char_width)
        max_chars = max(20, min(max_chars, 80))  # Clamp between 20-80

        results: dict[str, Path] = {}
        styles = [
            CaptionStyle.FORMAL,
            CaptionStyle.SARCASTIC,
            CaptionStyle.HUMOROUS_TECH,
            CaptionStyle.HUMOROUS_NON_TECH,
        ]

        for style in styles:
            caption = caption_set.get_caption(style)
            if caption is None:
                logger.warning("No caption found for style %s, skipping", style.value)
                continue

            output_path = get_styled_video_path(video_id, style.value)

            try:
                await self.burn_single(
                    video_path=video_path,
                    output_path=output_path,
                    caption_text=caption.text,
                    video_width=video_width,
                    video_height=video_height,
                    max_chars_per_line=max_chars,
                    transcript_segments=transcript_segments,
                    bottom_padding=bottom_padding,
                )
                results[style.value] = output_path
                logger.info(
                    "Burned %s caption into %s", style.value, output_path.name,
                )
            except Exception as exc:
                logger.error(
                    "Failed to burn %s caption: %s", style.value, exc,
                )
                raise RuntimeError(
                    f"Failed to burn {style.value} caption into video: {exc}"
                ) from exc

        logger.info(
            "All %d styled videos generated for video %s",
            len(results), video_id,
        )
        return results

    async def burn_single(
        self,
        video_path: Path,
        output_path: Path,
        caption_text: str,
        video_width: int = 1920,
        video_height: int = 1080,
        max_chars_per_line: int = 50,
        font_file: Optional[str] = None,
        transcript_segments: Optional[list] = None,
        bottom_padding: Optional[float] = None,
    ) -> Path:
        """
        Burn a single caption into a video file.

        Args:
            video_path: Path to the source video.
            output_path: Path for the output video.
            caption_text: The caption text to burn.
            video_width: Video width in pixels.
            video_height: Video height in pixels.
            max_chars_per_line: Max characters per line for wrapping.
            font_file: Override font file path.
            transcript_segments: Optional list of Whisper transcript segments.

        Returns:
            Path to the output video file.

        Raises:
            RuntimeError: If the ffmpeg command fails.
        """
        import re

        # Determine speech bounds
        start_time = 0.0
        end_time = 0.0

        if transcript_segments:
            start_time = transcript_segments[0]["start"] if isinstance(transcript_segments[0], dict) else transcript_segments[0].start
            end_time = transcript_segments[-1]["end"] if isinstance(transcript_segments[-1], dict) else transcript_segments[-1].end
        else:
            # Fall back to video duration
            info = await get_video_info(video_path)
            end_time = info.get("duration", 10.0)

        total_duration = end_time - start_time
        if total_duration <= 0:
            total_duration = 10.0

        # Split caption_text into sentences
        raw_lines = re.split(r'(?<=[.!?])\s+', caption_text)
        raw_lines = [s.strip() for s in raw_lines if s.strip()]

        # Split long lines into sub-phrases of ~8 words
        lines = []
        for line in raw_lines:
            words = line.split()
            if len(words) > 12:
                chunk_size = 8
                for i in range(0, len(words), chunk_size):
                    chunk = " ".join(words[i:i+chunk_size])
                    lines.append(chunk)
            else:
                lines.append(line)

        # Calculate word counts and proportions
        word_counts = [len(line.split()) for line in lines]
        total_words = sum(word_counts)

        filters = []
        font = font_file or self.font_file
        font_exists_path = font if Path(font).exists() else None

        if total_words > 0 and len(lines) > 0:
            current_time = start_time
            for line, count in zip(lines, word_counts):
                proportion = count / total_words
                duration = total_duration * proportion
                line_end = current_time + duration

                # Deduct a clean 0.1s offset to prevent overlapping boundaries (standard subtitle gap)
                line_end_clamped = max(current_time + 0.15, line_end - 0.10)

                # 0.3s fade-in/out transitions (scaled if duration is very short)
                fade_dur = min(0.3, (line_end_clamped - current_time) / 3.0)
                if fade_dur < 0.05:
                    fade_dur = 0.05

                # Pre-calculate time limits in Python to keep FFmpeg filter expressions simple and safe
                fade_in_end = current_time + fade_dur
                fade_out_start = line_end_clamped - fade_dur

                # Clamped alpha formula (fully transparent outside active segment range)
                alpha_expr = (
                    f"if(lt(t,{current_time:.3f}),0.0,"
                    f"if(gt(t,{line_end_clamped:.3f}),0.0,"
                    f"if(lt(t,{fade_in_end:.3f}),(t-{current_time:.3f})/{fade_dur:.3f},"
                    f"if(gt(t,{fade_out_start:.3f}),({line_end_clamped:.3f}-t)/{fade_dur:.3f},1.0))))"
                )

                wrapped_text = wrap_text(line, max_chars_per_line)
                drawtext = build_drawtext_filter(
                    text=wrapped_text,
                    font_file=font_exists_path,
                    font_size=self.font_size,
                    font_color=self.font_color,
                    border_width=self.border_width,
                    border_color=self.border_color,
                    video_width=video_width,
                    video_height=video_height,
                    enable=f"between(t,{current_time:.3f},{line_end_clamped:.3f})",
                    alpha=alpha_expr,
                    bottom_padding=bottom_padding,
                )
                filters.append(drawtext)
                current_time = line_end
        else:
            # Fallback to single static overlay with a 0.5s fade-in/fade-out
            info = await get_video_info(video_path)
            duration = info.get("duration", 10.0)
            fade_dur = min(0.5, duration / 2.0)
            if fade_dur < 0.05:
                fade_dur = 0.05

            fade_out_start = duration - fade_dur

            # Clamped alpha formula for static fallback
            alpha_expr = (
                f"if(lt(t,0.0),0.0,"
                f"if(gt(t,{duration:.3f}),0.0,"
                f"if(lt(t,{fade_dur:.3f}),t/{fade_dur:.3f},"
                f"if(gt(t,{fade_out_start:.3f}),({duration:.3f}-t)/{fade_dur:.3f},1.0))))"
            )

            wrapped_text = wrap_text(caption_text, max_chars_per_line)
            drawtext = build_drawtext_filter(
                text=wrapped_text,
                font_file=font_exists_path,
                font_size=self.font_size,
                font_color=self.font_color,
                border_width=self.border_width,
                border_color=self.border_color,
                video_width=video_width,
                video_height=video_height,
                alpha=alpha_expr,
                bottom_padding=bottom_padding,
            )
            filters.append(drawtext)

        drawtext_filter = ",".join(filters)

        # Build ffmpeg command
        args = [
            "-i", str(video_path),
            "-vf", drawtext_filter,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "copy",
            "-movflags", "+faststart",
            "-y",
            str(output_path),
        ]

        try:
            await run_ffmpeg_command(args, timeout=300)
        except Exception as exc:
            logger.error("Caption burning failed: %s", exc)
            raise RuntimeError(f"Failed to burn caption into video: {exc}") from exc

        if not output_path.exists():
            raise RuntimeError(f"Output file was not created: {output_path}")

        file_size = output_path.stat().st_size
        logger.info(
            "Caption burned successfully: %s (%.1f MB)",
            output_path.name, file_size / (1024 * 1024),
        )
        return output_path

    async def generate_thumbnail(
        self,
        video_path: Path,
        output_path: Path,
        timestamp: float = 1.0,
    ) -> Path:
        """
        Generate a thumbnail image from a video at a given timestamp.

        Args:
            video_path: Path to the video file.
            output_path: Path for the output thumbnail image.
            timestamp: Time in seconds to capture the frame.

        Returns:
            Path to the generated thumbnail.
        """
        args = [
            "-i", str(video_path),
            "-ss", str(timestamp),
            "-vframes", "1",
            "-vf", "scale=480:-1",
            "-q:v", "3",
            "-y",
            str(output_path),
        ]

        try:
            await run_ffmpeg_command(args, timeout=30)
        except Exception as exc:
            logger.error("Thumbnail generation failed: %s", exc)
            raise RuntimeError(f"Failed to generate thumbnail: {exc}") from exc

        return output_path

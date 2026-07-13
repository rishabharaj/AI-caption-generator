"""
CapturaAI — Whisper transcription client.

Transcribes audio using OpenAI Whisper (openai-whisper package, local model).
Uses the 'tiny' model optimized for speed on Heroku Standard-2x (1GB RAM).
Returns transcript with timestamps. Handles errors gracefully.
"""

import asyncio
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from backend.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Global model cache — load once, reuse across all requests
# ---------------------------------------------------------------------------
_whisper_model = None
_model_lock = asyncio.Lock() if hasattr(asyncio, 'Lock') else None


def _get_model_sync(model_name: str = "tiny"):
    """Load the Whisper model synchronously (called from thread pool)."""
    global _whisper_model
    if _whisper_model is not None:
        return _whisper_model

    import whisper

    logger.info("Loading Whisper '%s' model (first request — this takes ~5s)...", model_name)
    _whisper_model = whisper.load_model(model_name, device="cpu")
    logger.info("Whisper '%s' model loaded and cached globally.", model_name)
    return _whisper_model


class TranscriptSegment:
    """A single segment of the transcript with timing information."""

    def __init__(self, text: str, start: float, end: float):
        self.text = text.strip()
        self.start = start
        self.end = end

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "text": self.text,
            "start": round(self.start, 3),
            "end": round(self.end, 3),
        }

    def __repr__(self) -> str:
        return f"[{self.start:.1f}-{self.end:.1f}] {self.text[:50]}"


class TranscriptResult:
    """Complete transcription result."""

    def __init__(
        self,
        text: str = "",
        segments: list[TranscriptSegment] | None = None,
        language: str = "en",
        duration: float = 0.0,
    ):
        self.text = text
        self.segments = segments or []
        self.language = language
        self.duration = duration

    @property
    def word_count(self) -> int:
        """Count words in the full transcript."""
        return len(self.text.split()) if self.text else 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "text": self.text,
            "segments": [s.to_dict() for s in self.segments],
            "language": self.language,
            "duration": self.duration,
            "word_count": self.word_count,
        }


class WhisperClient:
    """
    Transcribes audio files using OpenAI's Whisper model (local, CPU).

    Uses the 'tiny' model (~39MB) for fast inference on Heroku Standard-2x.
    The model is loaded lazily on first transcription and cached globally.
    """

    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize the Whisper client.

        Args:
            model_name: Whisper model size. Defaults to config setting ('tiny').
        """
        self.model_name = model_name or settings.whisper.model_name
        self.language = settings.whisper.language

    async def transcribe(
        self, audio_path: Path, api_key: Optional[str] = None
    ) -> TranscriptResult:
        """
        Transcribe an audio file using local Whisper model.

        Runs the CPU-bound inference in a thread pool to avoid blocking the
        event loop. The api_key parameter is accepted for interface
        compatibility but is not used (local model, no cloud calls).

        Args:
            audio_path: Path to the WAV audio file.
            api_key: Ignored (kept for interface compatibility).

        Returns:
            TranscriptResult with text, segments, language, and duration.

        Raises:
            FileNotFoundError: If the audio file doesn't exist.
            RuntimeError: If Whisper is not installed or transcription fails.
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        logger.info("Starting local Whisper transcription for %s", audio_path.name)

        try:
            # Run CPU-bound transcription in a thread pool
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, self._transcribe_sync, audio_path)
            logger.info(
                "Local Whisper transcription complete: %d words, %d segments",
                result.word_count, len(result.segments),
            )
            return result
        except ImportError:
            raise RuntimeError(
                "openai-whisper package is required for transcription. "
                "Install with: pip install openai-whisper"
            )
        except Exception as exc:
            logger.error("Local Whisper transcription failed: %s", exc)
            raise RuntimeError(f"Transcription failed: {exc}") from exc

    def _transcribe_sync(self, audio_path: Path) -> TranscriptResult:
        """
        Synchronous transcription (called from thread pool).

        Uses fp32 on CPU for compatibility. The 'tiny' model processes
        ~32x real-time on CPU (a 60s clip takes ~2s).

        Args:
            audio_path: Path to the audio file.

        Returns:
            TranscriptResult instance.
        """
        model = _get_model_sync(self.model_name)

        # Build transcription options optimized for speed
        options: dict[str, Any] = {
            "verbose": False,
            "fp16": False,          # CPU doesn't support fp16
            "condition_on_previous_text": False,  # Faster, avoids hallucination loops
            "no_speech_threshold": 0.6,
            "compression_ratio_threshold": 2.4,
        }
        if self.language:
            options["language"] = self.language

        logger.debug("Transcribing %s with model='%s'", audio_path.name, self.model_name)
        raw_result = model.transcribe(str(audio_path), **options)

        # Parse segments
        segments = []
        for seg in raw_result.get("segments", []):
            segments.append(TranscriptSegment(
                text=seg.get("text", ""),
                start=seg.get("start", 0.0),
                end=seg.get("end", 0.0),
            ))

        full_text = raw_result.get("text", "").strip()
        detected_language = raw_result.get("language", "en")

        # Calculate total duration from last segment
        duration = segments[-1].end if segments else 0.0

        result = TranscriptResult(
            text=full_text,
            segments=segments,
            language=detected_language,
            duration=duration,
        )

        logger.info(
            "Transcription complete: %d words, %d segments, language=%s",
            result.word_count, len(result.segments), result.language,
        )
        return result

    def is_available(self) -> bool:
        """Check if the Whisper package is installed and usable."""
        try:
            import whisper  # noqa: F401
            return True
        except ImportError:
            return False

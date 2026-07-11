"""
CapturaAI — Whisper transcription client.

Transcribes audio using OpenAI Whisper (openai-whisper package, local model).
Returns transcript with timestamps. Handles errors gracefully.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Optional

from backend.config import settings

logger = logging.getLogger(__name__)


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
    Transcribes audio files using OpenAI's Whisper model (local).

    Uses the `openai-whisper` package for local inference. The model is loaded
    lazily on first transcription to avoid slow startup times.
    """

    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize the Whisper client.

        Args:
            model_name: Whisper model size ('tiny', 'base', 'small', 'medium', 'large').
                        Defaults to config setting.
        """
        self.model_name = model_name or settings.whisper.model_name
        self.language = settings.whisper.language
        self._model = None
        self._model_loaded = False

    def _load_model(self) -> Any:
        """
        Lazily load the Whisper model.

        Returns:
            The loaded Whisper model instance.

        Raises:
            ImportError: If the whisper package is not installed.
        """
        if self._model is not None:
            return self._model

        try:
            import whisper
        except ImportError:
            logger.error(
                "openai-whisper package not installed. "
                "Install with: pip install openai-whisper"
            )
            raise ImportError(
                "openai-whisper package is required for transcription. "
                "Install with: pip install openai-whisper"
            )

        logger.info("Loading Whisper model '%s'...", self.model_name)
        self._model = whisper.load_model(self.model_name)
        self._model_loaded = True
        logger.info("Whisper model '%s' loaded successfully", self.model_name)
        return self._model

    async def transcribe(self, audio_path: Path) -> TranscriptResult:
        """
        Transcribe an audio file using Whisper.

        Runs the CPU/GPU-intensive transcription in a thread pool to avoid
        blocking the async event loop.

        Args:
            audio_path: Path to the WAV audio file.

        Returns:
            TranscriptResult with full text and timed segments.

        Raises:
            FileNotFoundError: If the audio file doesn't exist.
            RuntimeError: If transcription fails.
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        logger.info("Starting transcription of %s", audio_path.name)

        try:
            # Run whisper transcription in a thread to avoid blocking
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None, self._transcribe_sync, audio_path
            )
            return result
        except ImportError:
            logger.warning("Whisper not available, returning empty transcript")
            return TranscriptResult(
                text="[Whisper not installed — using visual analysis only]",
                segments=[],
                language="en",
            )
        except Exception as exc:
            logger.error("Transcription failed for %s: %s", audio_path, exc)
            raise RuntimeError(f"Transcription failed: {exc}") from exc

    def _transcribe_sync(self, audio_path: Path) -> TranscriptResult:
        """
        Synchronous transcription (called from thread pool).

        Args:
            audio_path: Path to the audio file.

        Returns:
            TranscriptResult instance.
        """
        model = self._load_model()

        # Build transcription options
        options: dict[str, Any] = {
            "verbose": False,
        }
        if self.language:
            options["language"] = self.language

        logger.debug("Transcribing %s with options: %s", audio_path.name, options)
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

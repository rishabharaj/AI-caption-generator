"""
CapturaAI — OpenAI Whisper API transcription client.

Transcribes audio using OpenAI's Whisper API (whisper-1 model).
Returns transcript with timestamps. Handles errors gracefully.
"""

import logging
import os
from pathlib import Path
from typing import Any, Optional

import httpx

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
    Transcribes audio files using OpenAI's hosted Whisper API.
    Uses the 'whisper-1' model via HTTPS.
    """

    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize the Whisper client.
        """
        self.language = settings.whisper.language

    async def transcribe(
        self, audio_path: Path, api_key: Optional[str] = None
    ) -> TranscriptResult:
        """
        Transcribe an audio file using OpenAI's hosted Whisper API.
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # Force reload .env file to ensure latest keys are fetched
        from dotenv import load_dotenv
        env_path = Path(__file__).resolve().parent.parent.parent / ".env"
        load_dotenv(env_path, override=True)

        openai_api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not openai_api_key:
            logger.error("OPENAI_API_KEY environment variable is missing.")
            raise RuntimeError("OpenAI API Key is not configured.")

        url = "https://api.openai.com/v1/audio/transcriptions"
        headers = {
            "Authorization": f"Bearer {openai_api_key}",
            "Accept": "application/json",
        }

        logger.info("Starting OpenAI API Whisper transcription for %s", audio_path.name)

        async with httpx.AsyncClient(timeout=60.0) as client:
            with open(audio_path, "rb") as f:
                files = {
                    "file": (audio_path.name, f, "audio/wav")
                }
                data = {
                    "model": "whisper-1",
                    "response_format": "verbose_json"
                }
                if self.language:
                    data["language"] = self.language

                response = await client.post(url, headers=headers, files=files, data=data)
                response.raise_for_status()

        raw_result = response.json()
        full_text = raw_result.get("text", "").strip()
        detected_language = raw_result.get("language", "en")

        segments = []
        if "segments" in raw_result:
            for seg in raw_result.get("segments", []):
                segments.append(TranscriptSegment(
                    text=seg.get("text", ""),
                    start=seg.get("start", 0.0),
                    end=seg.get("end", 0.0),
                ))
        else:
            duration = raw_result.get("duration", 0.0)
            if full_text:
                segments.append(TranscriptSegment(
                    text=full_text,
                    start=0.0,
                    end=duration,
                ))

        duration = raw_result.get("duration", (segments[-1].end if segments else 0.0))

        logger.info(
            "OpenAI API Whisper transcription complete: %d words, %d segments, language=%s",
            len(full_text.split()) if full_text else 0, len(segments), detected_language
        )

        return TranscriptResult(
            text=full_text,
            segments=segments,
            language=detected_language,
            duration=duration,
        )

    def is_available(self) -> bool:
        """The client is always available as it calls OpenAI via API."""
        return True

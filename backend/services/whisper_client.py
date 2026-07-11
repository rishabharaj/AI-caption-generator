"""
CapturaAI — Whisper transcription client.

Transcribes audio using OpenAI Whisper (openai-whisper package, local model).
Returns transcript with timestamps. Handles errors gracefully.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Optional

import httpx

from backend.config import settings
import backend.utils.ffmpeg_utils

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

    async def transcribe(
        self, audio_path: Path, api_key: Optional[str] = None
    ) -> TranscriptResult:
        """
        Transcribe an audio file using Whisper Cloud APIs (Sarvam, Groq, Fireworks).
        Local Whisper fallback is disabled.
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # Force reload .env file to ensure latest keys are fetched
        import os
        from dotenv import load_dotenv
        env_path = Path(__file__).resolve().parent.parent.parent / ".env"
        load_dotenv(env_path, override=True)

        # 1. Try Sarvam Cloud Transcription if SARVAM_API_KEY is configured
        sarvam_api_key = os.environ.get("SARVAM_API_KEY", "").strip()
        if sarvam_api_key:
            try:
                return await self._transcribe_sarvam(audio_path, sarvam_api_key)
            except Exception as exc:
                logger.error("Cloud transcription via Sarvam AI failed: %s", exc)
                raise RuntimeError(f"Sarvam AI transcription failed: {exc}") from exc

        # 2. Try Groq Cloud Transcription if GROQ_API_KEY is configured
        groq_api_key = os.environ.get("GROQ_API_KEY", "").strip()
        if groq_api_key:
            try:
                return await self._transcribe_groq(audio_path, groq_api_key)
            except Exception as exc:
                logger.error("Cloud transcription via Groq AI failed: %s", exc)
                raise RuntimeError(f"Groq AI transcription failed: {exc}") from exc

        # 3. Try Fireworks Cloud Transcription
        if api_key:
            try:
                return await self._transcribe_cloud(audio_path, api_key)
            except Exception as exc:
                logger.error("Cloud transcription via Fireworks AI failed: %s", exc)
                raise RuntimeError(f"Fireworks AI transcription failed: {exc}") from exc

        # Local Whisper fallback is disabled as requested by the user
        logger.error("No active Cloud STT API keys (Sarvam, Groq, Fireworks) were found or configured.")
        raise RuntimeError("No Cloud STT API keys configured. Local Whisper is disabled.")

    async def _transcribe_sarvam(self, audio_path: Path, api_key: str) -> TranscriptResult:
        """
        Transcribe an audio file using Sarvam AI Speech-to-Text API.
        """
        url = "https://api.sarvam.ai/speech-to-text"
        headers = {
            "api-subscription-key": api_key,
            "Accept": "application/json",
        }
        
        logger.info("Starting cloud transcription via Sarvam AI for %s", audio_path.name)
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            with open(audio_path, "rb") as f:
                files = {
                    "file": (audio_path.name, f, "audio/wav")
                }
                data = {
                    "model": "saaras:v3",
                    "language_code": "unknown", # Auto-detect
                    "mode": "transcribe"
                }
                
                response = await client.post(url, headers=headers, files=files, data=data)
                response.raise_for_status()
                
        raw_result = response.json()
        full_text = raw_result.get("transcript", "").strip()
        
        # Parse segments from timestamps if present
        segments = []
        timestamps = raw_result.get("timestamps")
        if timestamps and isinstance(timestamps, dict) and "words" in timestamps:
            words = timestamps.get("words", [])
            if words:
                chunk_size = 10
                for i in range(0, len(words), chunk_size):
                    chunk = words[i:i + chunk_size]
                    if chunk:
                        text = " ".join([w.get("word", "") for w in chunk]).strip()
                        start = float(chunk[0].get("start_time_seconds", 0.0))
                        end = float(chunk[-1].get("end_time_seconds", start + 2.0))
                        segments.append(TranscriptSegment(text=text, start=start, end=end))
        
        # If no word-level timestamps were parsed, create a single segment covering the entire file
        if not segments:
            duration = 0.0
            try:
                import wave
                with wave.open(str(audio_path), "rb") as wave_file:
                    frames = wave_file.getnframes()
                    rate = wave_file.getframerate()
                    duration = frames / float(rate)
            except Exception:
                duration = 30.0
            
            if full_text:
                segments.append(TranscriptSegment(
                    text=full_text,
                    start=0.0,
                    end=duration,
                ))
        else:
            duration = segments[-1].end if segments else 0.0
            
        logger.info(
            "Sarvam cloud transcription complete: %d words, segments=%d",
            len(full_text.split()) if full_text else 0, len(segments)
        )
        
        return TranscriptResult(
            text=full_text,
            segments=segments,
            language="en", # Sarvam default representation
            duration=duration,
        )

    async def _transcribe_groq(self, audio_path: Path, api_key: str) -> TranscriptResult:
        """
        Transcribe an audio file using Groq Cloud Whisper API.
        """
        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        }
        
        model_name = "whisper-large-v3"
        logger.info("Starting cloud transcription via Groq AI for %s", audio_path.name)
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            with open(audio_path, "rb") as f:
                files = {
                    "file": (audio_path.name, f, "audio/wav")
                }
                data = {
                    "model": model_name,
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
            "Groq cloud transcription complete: %d words, language=%s",
            len(full_text.split()) if full_text else 0, detected_language
        )
        
        return TranscriptResult(
            text=full_text,
            segments=segments,
            language=detected_language,
            duration=duration,
        )

    async def _transcribe_cloud(self, audio_path: Path, api_key: str) -> TranscriptResult:
        """
        Transcribe an audio file using Fireworks AI Cloud Whisper API.
        """
        url = f"{settings.fireworks.base_url}/audio/transcriptions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        }
        
        # Use whisper-v3 model
        model_name = "accounts/fireworks/models/whisper-v3"
        
        logger.info("Starting cloud transcription via Fireworks AI for %s", audio_path.name)
        
        try:
            # Try with verbose_json to get segment timestamps
            response = await self._make_cloud_request(url, headers, audio_path, model_name, "verbose_json")
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            # Fall back to standard json if verbose_json is not supported (400 Bad Request)
            if exc.response.status_code == 400:
                logger.warning("verbose_json not supported by Fireworks AI, retrying with standard json")
                response = await self._make_cloud_request(url, headers, audio_path, model_name, "json")
                response.raise_for_status()
            else:
                raise
                
        raw_result = response.json()
        full_text = raw_result.get("text", "").strip()
        detected_language = raw_result.get("language", "en")
        
        # Parse segments
        segments = []
        if "segments" in raw_result:
            for seg in raw_result.get("segments", []):
                segments.append(TranscriptSegment(
                    text=seg.get("text", ""),
                    start=seg.get("start", 0.0),
                    end=seg.get("end", 0.0),
                ))
        else:
            # Fallback segment if segments are missing
            duration = raw_result.get("duration", 0.0)
            if full_text:
                segments.append(TranscriptSegment(
                    text=full_text,
                    start=0.0,
                    end=duration,
                ))
                
        duration = raw_result.get("duration", (segments[-1].end if segments else 0.0))
        
        logger.info(
            "Cloud transcription complete: %d words, %d segments, language=%s",
            len(full_text.split()) if full_text else 0, len(segments), detected_language
        )
        
        return TranscriptResult(
            text=full_text,
            segments=segments,
            language=detected_language,
            duration=duration,
        )
        
    async def _make_cloud_request(
        self, url: str, headers: dict, audio_path: Path, model_name: str, response_format: str
    ) -> httpx.Response:
        """Helper to make a single multipart POST request to the cloud transcription endpoint."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            with open(audio_path, "rb") as f:
                files = {
                    "file": (audio_path.name, f, "audio/wav")
                }
                data = {
                    "model": model_name,
                    "response_format": response_format
                }
                if self.language:
                    data["language"] = self.language
                
                return await client.post(url, headers=headers, files=files, data=data)

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

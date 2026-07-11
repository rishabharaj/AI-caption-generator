"""
CapturaAI — Fireworks AI API client.

Complete client for the Fireworks AI inference API.
Model: accounts/fireworks/models/llama-v3p1-8b-instruct
Includes retry logic, timeout handling, and proper error reporting.
"""

import asyncio
import logging
from typing import Any, Optional

import httpx

from backend.config import settings

logger = logging.getLogger(__name__)

# System prompts for each caption style — exactly from the specification
SYSTEM_PROMPTS: dict[str, str] = {
    "formal": (
        "You are a professional documentary narrator. Describe the video in a "
        "formal, objective, and eloquent manner. Use proper grammar, sophisticated "
        "vocabulary, and a neutral tone. Focus on the key events, actions, and "
        "visual elements. Keep it concise (2-3 sentences)."
    ),
    "sarcastic": (
        "You are a witty, sarcastic commentator. Write a dry, ironic caption "
        "about this video. Use understated humor, subtle mockery, and a deadpan "
        "tone. Make it clever but not mean-spirited. 1-2 sentences max."
    ),
    "humorous_tech": (
        "You are a tech-savvy comedian. Write a funny caption with references "
        "to startups, programming, AI, Silicon Valley culture, or geek life. "
        "Use tech jargon humorously. Make it relatable to developers and tech "
        "enthusiasts. 1-2 sentences."
    ),
    "humorous_non_tech": (
        "You are a general audience comedian. Write a funny, accessible caption "
        "that anyone can understand. No tech jargon. Use observational humor, "
        "pop culture references, or witty wordplay. Keep it light and universally "
        "funny. 1-2 sentences."
    ),
}


class FireworksClient:
    """
    Client for the Fireworks AI inference API.

    Handles caption generation with retry logic, timeouts, and proper error handling.
    """

    def __init__(self, api_key: str):
        """
        Initialize the Fireworks client.

        Args:
            api_key: Fireworks AI API key (should start with 'fw_').
        """
        self.api_key = api_key
        self.base_url = settings.fireworks.base_url
        self.model = settings.model.base_model
        self.max_tokens = settings.model.max_tokens
        self.temperature = settings.model.temperature
        self.timeout = settings.fireworks.timeout_seconds
        self.max_retries = settings.fireworks.max_retries
        self.retry_delay = settings.fireworks.retry_delay_seconds

    def _build_headers(self) -> dict[str, str]:
        """Build request headers with authorization."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _build_user_prompt(
        self, transcript: str, visual_context: list[str],
    ) -> str:
        """
        Build the user prompt from transcript and visual context.

        Args:
            transcript: The transcribed audio text.
            visual_context: List of visual frame descriptions.

        Returns:
            Formatted user prompt string.
        """
        parts = []

        if transcript and transcript.strip():
            parts.append(f"Video transcript: {transcript.strip()}")
        else:
            parts.append("Video transcript: [No speech detected — mute video]")

        if visual_context:
            ctx = "; ".join(visual_context[:10])  # Limit context length
            parts.append(f"Visual context: {ctx}")

        parts.append(
            "\nWrite a caption for this video. Return ONLY the caption text, "
            "no labels, no quotes, no explanations."
        )

        return "\n".join(parts)

    async def generate_caption(
        self,
        style: str,
        transcript: str,
        visual_context: list[str],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate a caption for a given style using the Fireworks AI API.

        Args:
            style: One of 'formal', 'sarcastic', 'humorous_tech', 'humorous_non_tech'.
            transcript: The video transcript text.
            visual_context: List of visual descriptions from key frames.
            temperature: Override temperature (optional).
            max_tokens: Override max tokens (optional).

        Returns:
            The generated caption text.

        Raises:
            ValueError: If the style is not recognized.
            RuntimeError: If the API call fails after all retries.
        """
        if style not in SYSTEM_PROMPTS:
            raise ValueError(
                f"Unknown caption style '{style}'. "
                f"Must be one of: {list(SYSTEM_PROMPTS.keys())}"
            )

        system_prompt = SYSTEM_PROMPTS[style]
        user_prompt = self._build_user_prompt(transcript, visual_context)

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": max_tokens or self.max_tokens,
            "temperature": temperature if temperature is not None else self.temperature,
        }

        last_error: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                caption = await self._make_request(payload)
                logger.info(
                    "Generated %s caption (attempt %d): %s",
                    style, attempt, caption[:80],
                )
                return caption.strip()
            except httpx.TimeoutException as exc:
                last_error = exc
                logger.warning(
                    "Fireworks API timeout (attempt %d/%d) for style '%s': %s",
                    attempt, self.max_retries, style, exc,
                )
            except httpx.HTTPStatusError as exc:
                last_error = exc
                status = exc.response.status_code
                if status in (429, 500, 502, 503):
                    # Retryable errors
                    logger.warning(
                        "Fireworks API error %d (attempt %d/%d) for style '%s'",
                        status, attempt, self.max_retries, style,
                    )
                else:
                    # Non-retryable
                    logger.error(
                        "Fireworks API error %d for style '%s': %s",
                        status, style, exc.response.text[:300],
                    )
                    raise RuntimeError(
                        f"Fireworks API error ({status}): {exc.response.text[:300]}"
                    ) from exc
            except Exception as exc:
                last_error = exc
                logger.error(
                    "Unexpected error (attempt %d/%d) for style '%s': %s",
                    attempt, self.max_retries, style, exc,
                )

            # Wait before retrying with exponential backoff
            if attempt < self.max_retries:
                delay = self.retry_delay * (2 ** (attempt - 1))
                logger.debug("Retrying in %.1fs...", delay)
                await asyncio.sleep(delay)

        raise RuntimeError(
            f"Failed to generate {style} caption after {self.max_retries} attempts: "
            f"{last_error}"
        )

    async def _make_request(self, payload: dict[str, Any]) -> str:
        """
        Make a single API request to Fireworks.

        Args:
            payload: The JSON request payload.

        Returns:
            The generated text from the response.

        Raises:
            httpx.HTTPStatusError: On HTTP errors.
            httpx.TimeoutException: On timeout.
            RuntimeError: On unexpected response format.
        """
        url = f"{self.base_url}/chat/completions"
        headers = self._build_headers()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()

        data = response.json()

        # Extract the generated text
        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError("Fireworks API returned no choices in response")

        message = choices[0].get("message", {})
        content = message.get("content", "")

        if not content:
            raise RuntimeError("Fireworks API returned empty content")

        return content

    async def health_check(self) -> bool:
        """
        Check if the Fireworks API is reachable and the key is valid.

        Returns:
            True if the API responds successfully.
        """
        try:
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": "Hello"},
                ],
                "max_tokens": 5,
            }
            await self._make_request(payload)
            return True
        except Exception as exc:
            logger.warning("Fireworks health check failed: %s", exc)
            return False

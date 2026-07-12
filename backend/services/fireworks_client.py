"""
CapturaAI — Fireworks AI API client.

Complete client for the Fireworks AI inference API.
Model: accounts/fireworks/models/llama-v3p1-8b-instruct
Includes retry logic, timeout handling, and proper error reporting.
"""

import asyncio
import logging
import re
from typing import Any, Optional

import httpx

from backend.config import settings

logger = logging.getLogger(__name__)

# System prompts for each caption style — exactly from the specification
SYSTEM_PROMPTS: dict[str, str] = {
    "formal": (
        "You are a professional documentary narrator. Write a concise video caption "
        "in 2-3 sentences. Use formal, objective, and eloquent language with proper "
        "grammar, sophisticated vocabulary, and a neutral tone. Focus on the key "
        "events, actions, and visual elements described.\n\n"
        "CRITICAL RULES:\n"
        "- Output ONLY the final caption text.\n"
        "- Do NOT include any analysis, reasoning, thought process, bullet points, "
        "labels, or meta-commentary.\n"
        "- Do NOT reference the prompt, frames, or instructions.\n"
        "- Do NOT start with phrases like 'Analyze', 'The prompt says', or 'Let me'.\n"
        "- Just write the caption directly as a documentary narrator would speak it."
    ),
    "sarcastic": (
        "You are a witty, sarcastic commentator. Write a dry, ironic caption "
        "about this video. Use understated humor, subtle mockery, and a deadpan "
        "tone. Make it clever but not mean-spirited. 1-2 sentences max.\n\n"
        "CRITICAL: Output ONLY the caption text. No analysis, no reasoning, "
        "no labels, no meta-commentary."
    ),
    "humorous_tech": (
        "You are a tech-savvy comedian. Write a funny caption with references "
        "to startups, programming, AI, Silicon Valley culture, or geek life. "
        "Use tech jargon humorously. Make it relatable to developers and tech "
        "enthusiasts. 1-2 sentences.\n\n"
        "CRITICAL: Output ONLY the caption text. No analysis, no reasoning, "
        "no labels, no meta-commentary."
    ),
    "humorous_non_tech": (
        "You are a general audience comedian. Write a funny, accessible caption "
        "that anyone can understand. No tech jargon. Use observational humor, "
        "pop culture references, or witty wordplay. Keep it light and universally "
        "funny. 1-2 sentences.\n\n"
        "CRITICAL: Output ONLY the caption text. No analysis, no reasoning, "
        "no labels, no meta-commentary."
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

        # Filter out placeholder/empty visual context entries
        meaningful_context = [
            ctx for ctx in (visual_context or [])
            if ctx and "visual content from video" not in ctx.lower()
        ]
        if meaningful_context:
            ctx = "; ".join(meaningful_context[:10])
            parts.append(f"Visual context: {ctx}")
        else:
            parts.append(
                f"Visual context: Video contains {len(visual_context or [])} frames"
            )

        parts.append(
            "\nWrite a caption for this video. "
            "Return ONLY the caption text — no reasoning, no bullet points, "
            "no analysis, no labels, no quotes, no explanations."
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

        # Use smaller max_tokens for captions (2-3 sentences don't need 800)
        effective_max_tokens = max_tokens or min(self.max_tokens, 200)

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": effective_max_tokens,
            "temperature": temperature if temperature is not None else self.temperature,
        }

        last_error: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                raw_caption = await self._make_request(payload)
                caption = self._clean_caption(raw_caption)
                logger.info(
                    "Generated %s caption (attempt %d): %s",
                    style, attempt, caption[:80],
                )
                return caption
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

    @staticmethod
    def _clean_caption(raw: str) -> str:
        """
        Post-process LLM output to strip reasoning artifacts.

        Some models (especially reasoning/thinking models like GLM) may
        include chain-of-thought, bullet points, numbered lists, or
        markdown formatting. This method strips all of that, leaving
        only clean prose suitable for a video caption.

        Args:
            raw: Raw text from the LLM response.

        Returns:
            Clean caption text.
        """
        text = raw.strip()

        # If the output contains markdown headers or bullet analysis,
        # try to extract just the final "caption" portion
        # Common patterns: reasoning ends with the actual caption at the bottom
        reasoning_markers = [
            "**Analyze", "**Role:", "**Tone", "**Content:", "**Constraint:",
            "**Input:", "* **", "**Correction", "Let me re-read",
            "Let's re-read", "Let's try", "Let me refine",
            "Wait,", "-> This is",
        ]

        has_reasoning = any(marker in text for marker in reasoning_markers)

        if has_reasoning:
            # The actual caption is usually the last clean paragraph
            # Split by double newlines and find the last prose paragraph
            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
            clean_paragraphs = []
            for para in reversed(paragraphs):
                # Skip paragraphs that look like reasoning
                if any(marker in para for marker in reasoning_markers):
                    continue
                if para.startswith(("*", "-", "1.", "2.", "3.")):
                    continue
                if ":" in para.split(".")[0] and len(para.split(".")[0]) < 30:
                    # Likely a label like "Caption:" — extract after the colon
                    after_colon = para.split(":", 1)[1].strip()
                    if after_colon:
                        clean_paragraphs.insert(0, after_colon)
                        continue
                clean_paragraphs.insert(0, para)

            if clean_paragraphs:
                text = " ".join(clean_paragraphs)
            else:
                # Fallback: just take the last non-empty line
                lines = [l.strip() for l in raw.strip().splitlines() if l.strip()]
                text = lines[-1] if lines else raw.strip()

        # Remove residual markdown formatting
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # **bold**
        text = re.sub(r'\*(.+?)\*', r'\1', text)  # *italic*
        text = re.sub(r'^#+\s*', '', text)  # # headers
        text = re.sub(r'^\s*[-*]\s+', '', text, flags=re.MULTILINE)  # bullet points
        text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)  # numbered lists

        # Strip surrounding quotes if present
        if (text.startswith('"') and text.endswith('"')) or \
           (text.startswith("'") and text.endswith("'")):
            text = text[1:-1]

        # Collapse multiple spaces/newlines into single spaces
        text = re.sub(r'\s+', ' ', text).strip()

        return text

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

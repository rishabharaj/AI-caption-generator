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
# Hard limit: 100 words max for all captions
SYSTEM_PROMPTS: dict[str, str] = {
    "formal": (
        "Respond with ONLY the caption text. No reasoning. No analysis. No thinking.\n\n"
        "You are a professional documentary narrator. Write a concise video caption "
        "in 2-3 sentences (100 words max). Use formal, eloquent language with "
        "sophisticated vocabulary and a neutral tone.\n\n"
        "If the video is silent/mute: write a rich, evocative caption about the "
        "visual atmosphere, movement, and mood — as if narrating a cinematic montage.\n\n"
        "NEVER output reasoning, bullet points, meta-commentary, or reference these "
        "instructions. NEVER say you lack information. Just write the caption."
    ),
    "sarcastic": (
        "Respond with ONLY the caption text. No reasoning. No analysis. No thinking.\n\n"
        "You are a witty, sarcastic commentator. Write a dry, ironic caption. "
        "Use understated humor, subtle mockery, deadpan tone. Clever but not mean. "
        "1-2 sentences, 100 words max.\n\n"
        "If the video is silent: lean into the silence with a witty remark about "
        "the visual aesthetic.\n\n"
        "NEVER output reasoning, bullet points, meta-commentary, or reference these "
        "instructions. NEVER say you lack information. Just write the caption."
    ),
    "humorous_tech": (
        "Respond with ONLY the caption text. No reasoning. No analysis. No thinking.\n\n"
        "You are a tech-savvy comedian. Write a funny caption with references to "
        "startups, programming, AI, or Silicon Valley culture. Use tech jargon "
        "humorously. 1-2 sentences, 100 words max.\n\n"
        "If the video is silent: riff on the silence with tech humor — buffering "
        "jokes, muted mics, silent deployments.\n\n"
        "NEVER output reasoning, bullet points, meta-commentary, or reference these "
        "instructions. NEVER say you lack information. Just write the caption."
    ),
    "humorous_non_tech": (
        "Respond with ONLY the caption text. No reasoning. No analysis. No thinking.\n\n"
        "You are a general audience comedian. Write a funny, accessible caption. "
        "No tech jargon. Use observational humor, pop culture references, or witty "
        "wordplay. 1-2 sentences, 100 words max.\n\n"
        "If the video is silent: use the silence as comedy material — comment on "
        "the mood or visual vibe.\n\n"
        "NEVER output reasoning, bullet points, meta-commentary, or reference these "
        "instructions. NEVER say you lack information. Just write the caption."
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

        Handles mute videos specially by providing rich guidance so the LLM
        generates meaningful captions even without speech or detailed
        visual descriptions.

        Args:
            transcript: The transcribed audio text.
            visual_context: List of visual frame descriptions.

        Returns:
            Formatted user prompt string.
        """
        parts = []

        has_transcript = bool(transcript and transcript.strip())

        if has_transcript:
            parts.append(f"Video transcript: {transcript.strip()}")
        else:
            parts.append("This is a silent/mute video with no spoken dialogue.")

        # Filter out placeholder/empty visual context entries
        meaningful_context = [
            ctx for ctx in (visual_context or [])
            if ctx
            and "visual content from video" not in ctx.lower()
            and not ctx.strip().lower().startswith("frame")
            or (
                ctx
                and ctx.strip().lower().startswith("frame")
                and len(ctx.split(":", 1)) > 1
                and len(ctx.split(":", 1)[1].strip()) > 30
            )
        ]

        if meaningful_context:
            ctx = "; ".join(meaningful_context[:10])
            parts.append(f"Visual context: {ctx}")
        else:
            # Provide rich guidance for the LLM when visual descriptions are
            # generic placeholders (e.g. "Frame 1: visual content from video")
            frame_count = len(visual_context or [])
            if not has_transcript:
                # Fully mute video with no meaningful visual descriptions —
                # give the LLM maximum creative direction
                parts.append(
                    f"The video consists of {frame_count} visual frames. "
                    "Since this is a visual-only video, focus on the cinematic "
                    "qualities: the movement, lighting, composition, atmosphere, "
                    "color palette, and overall mood conveyed by the imagery. "
                    "Imagine the scenes and write as if you are watching a "
                    "beautifully composed visual montage."
                )
            else:
                parts.append(
                    f"Visual context: The video contains {frame_count} "
                    "visual frames accompanying the spoken content."
                )

        parts.append(
            "\nWrite a caption for this video. "
            "Return ONLY the caption text — no reasoning, no bullet points, "
            "no analysis, no labels, no quotes, no explanations. "
            "Do NOT mention that you lack information or visual details. "
            "Write a confident, complete caption."
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

        The GLM-5p2 model frequently includes extensive chain-of-thought
        reasoning, instruction restating, and meta-commentary before
        producing the actual caption. This method aggressively strips
        all of that, leaving only clean prose suitable for a video caption.

        Args:
            raw: Raw text from the LLM response.

        Returns:
            Clean caption text.
        """
        text = raw.strip()

        # ---- Phase 1: Detect and strip reasoning blocks ----
        # These patterns indicate the model is "thinking out loud"
        reasoning_markers = [
            # Chain-of-thought patterns
            "**Analyze", "**Role:", "**Tone", "**Content:", "**Constraint:",
            "**Input:", "* **", "**Correction", "Let me re-read",
            "Let's re-read", "Let's try", "Let me refine", "Let me write",
            "Wait,", "Wait -", "But wait", "-> This is",
            # Instruction restating
            "The rules say", "The instructions", "the instructions",
            "I should:", "I need to", "I must", "I'll need to",
            "However, the instructions", "the user says",
            # Meta-commentary about lacking info
            "I cannot describe", "I can't describe", "no visual context",
            "without seeing", "no information provided", "haven't actually",
            "nothing has been described", "cannot write a meaningful",
            "no actual description", "not provided any visual",
            "The user wants me to", "The transcript says",
            "no specific visual", "don't have actual visual",
            "hasn't actually provided", "Since I don't",
            "Since no specific", "Since this is a",
            # Model self-awareness
            "Output ONLY", "output ONLY", "be confident",
            "don't mention lacking", "Write a confident",
        ]

        has_reasoning = any(marker in text for marker in reasoning_markers)

        if has_reasoning:
            # Strategy 1: Look for a labeled caption (e.g., "Caption: ...")
            caption_label_patterns = [
                r'(?:Caption|CAPTION|Here\'s the caption|Final caption|The caption)[:\s]*["\']?(.+)',
                r'(?:Here(?:\'s| is)(?: the| my)? (?:caption|result))[:\s]*["\']?(.+)',
            ]
            for pattern in caption_label_patterns:
                match = re.search(pattern, text, re.DOTALL)
                if match:
                    extracted = match.group(1).strip()
                    # Take only the first 1-3 sentences after the label
                    sentences = re.split(r'(?<=[.!?])\s+', extracted)
                    clean_sentences = []
                    for s in sentences:
                        if not any(m in s for m in reasoning_markers):
                            clean_sentences.append(s)
                        if len(clean_sentences) >= 3:
                            break
                    if clean_sentences:
                        text = ' '.join(clean_sentences)
                        break
            else:
                # Strategy 2: Split into paragraphs, take the last clean one
                paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
                clean_paragraphs = []
                for para in reversed(paragraphs):
                    # Skip paragraphs that contain ANY reasoning marker
                    if any(marker in para for marker in reasoning_markers):
                        continue
                    # Skip bullet-point lists or numbered lists
                    if para.startswith(("*", "-", "1.", "2.", "3.", "4.", "5.")):
                        continue
                    # Skip single-line labels
                    if len(para.split()) < 4:
                        continue
                    clean_paragraphs.insert(0, para)
                    # Only keep the last clean paragraph (the actual caption)
                    break

                if clean_paragraphs:
                    text = ' '.join(clean_paragraphs)
                else:
                    # Strategy 3: Sentence-level filtering — take the last
                    # 1-3 sentences that don't contain reasoning
                    all_sentences = re.split(r'(?<=[.!?])\s+', text)
                    clean_sentences = []
                    for sent in reversed(all_sentences):
                        sent = sent.strip()
                        if not sent:
                            continue
                        if any(m in sent for m in reasoning_markers):
                            continue
                        if sent.startswith(("*", "-", "1.", "2.", "3.")):
                            continue
                        clean_sentences.insert(0, sent)
                        if len(clean_sentences) >= 3:
                            break

                    if clean_sentences:
                        text = ' '.join(clean_sentences)
                    else:
                        # Last resort: take the very last line
                        lines = [l.strip() for l in raw.strip().splitlines() if l.strip()]
                        text = lines[-1] if lines else raw.strip()

        # ---- Phase 2: Clean up formatting ----
        # Remove residual markdown formatting
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # **bold**
        text = re.sub(r'\*(.+?)\*', r'\1', text)  # *italic*
        text = re.sub(r'^#+\s*', '', text)  # # headers
        text = re.sub(r'^\s*[-*]\s+', '', text, flags=re.MULTILINE)  # bullet points
        text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)  # numbered lists

        # Remove "Caption:" or similar labels at the start
        text = re.sub(
            r'^(?:Caption|CAPTION|Here\'s the caption|Final caption)[:\s]*',
            '', text, flags=re.IGNORECASE,
        )

        # Strip surrounding quotes if present
        if (text.startswith('"') and text.endswith('"')) or \
           (text.startswith("'") and text.endswith("'")):
            text = text[1:-1]

        # Collapse multiple spaces/newlines into single spaces
        text = re.sub(r'\s+', ' ', text).strip()

        # ---- Phase 3: Enforce length limit ----
        # Enforce hard 100-word maximum
        words = text.split()
        if len(words) > 100:
            # Try to cut at a sentence boundary within 100 words
            truncated = ' '.join(words[:100])
            # Find the last sentence-ending punctuation
            last_period = max(
                truncated.rfind('.'),
                truncated.rfind('!'),
                truncated.rfind('?'),
            )
            if last_period > len(truncated) // 2:
                # Cut at the last complete sentence
                text = truncated[:last_period + 1]
            else:
                # No good sentence boundary — just truncate at 100 words
                text = truncated + '...'

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

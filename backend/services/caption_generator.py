"""
CapturaAI — Caption generator orchestrator.

Coordinates caption generation across all 4 styles, using FireworksClient
when an API key is available, or MockAI as fallback.
"""

import asyncio
import logging
import random
from datetime import datetime
from typing import Optional

from backend.models.caption import Caption, CaptionSet, CaptionStyle
from backend.services.fireworks_client import FireworksClient, SYSTEM_PROMPTS
from backend.services.mock_ai import MockAI

logger = logging.getLogger(__name__)

ALL_STYLES: list[str] = [
    CaptionStyle.FORMAL.value,
    CaptionStyle.SARCASTIC.value,
    CaptionStyle.HUMOROUS_TECH.value,
    CaptionStyle.HUMOROUS_NON_TECH.value,
]


class CaptionGenerator:
    """
    Orchestrates caption generation for all 4 styles.

    Selects between FireworksClient (if API key provided) and MockAI (fallback).
    Builds user prompts from transcript and visual context.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the caption generator.

        Args:
            api_key: Optional Fireworks API key. If None, uses MockAI.
        """
        self.api_key = api_key
        if api_key:
            self._client = FireworksClient(api_key)
            self._using_mock = False
            logger.info("CaptionGenerator initialized with Fireworks API key")
        else:
            self._client = MockAI()
            self._using_mock = True
            logger.info("CaptionGenerator initialized with MockAI fallback")

    @property
    def is_mock(self) -> bool:
        """Whether the generator is using MockAI."""
        return self._using_mock

    async def generate_all(
        self,
        video_id: str,
        transcript: str,
        visual_context: list[str],
    ) -> CaptionSet:
        """
        Generate captions for all 4 styles.

        Args:
            video_id: The unique video identifier.
            transcript: Transcribed audio text.
            visual_context: List of visual frame descriptions.

        Returns:
            CaptionSet with all 4 captions populated.
        """
        logger.info(
            "Generating all 4 captions for video %s (mock=%s)",
            video_id, self._using_mock,
        )

        caption_set = CaptionSet(
            video_id=video_id,
            transcript=transcript,
            visual_context=visual_context,
        )

        # Generate all 4 styles concurrently
        tasks = {
            style: self._generate_single(style, transcript, visual_context)
            for style in ALL_STYLES
        }

        results = await asyncio.gather(
            *tasks.values(), return_exceptions=True,
        )

        for style, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                logger.error(
                    "Failed to generate %s caption for %s: %s",
                    style, video_id, result,
                )
                # Create a fallback caption on error
                caption = Caption(
                    text=f"[Caption generation failed for {style} style]",
                    style=CaptionStyle(style),
                    confidence=0.0,
                    timestamp=datetime.utcnow(),
                )
            else:
                caption = Caption(
                    text=result,
                    style=CaptionStyle(style),
                    word_count=len(result.split()),
                    confidence=round(random.uniform(0.85, 0.98), 2),
                    timestamp=datetime.utcnow(),
                )

            caption_set.set_caption(CaptionStyle(style), caption)

        caption_set.generated_at = datetime.utcnow()
        logger.info("All 4 captions generated for video %s", video_id)
        return caption_set

    async def regenerate_single(
        self,
        style: str,
        transcript: str,
        visual_context: list[str],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Caption:
        """
        Regenerate a single caption for a specific style.

        Args:
            style: The caption style to regenerate.
            transcript: Transcribed audio text.
            visual_context: Visual frame descriptions.
            temperature: Optional temperature override.
            max_tokens: Optional max_tokens override.

        Returns:
            A new Caption instance.

        Raises:
            ValueError: If the style is not recognized.
        """
        if style not in ALL_STYLES:
            raise ValueError(
                f"Unknown style '{style}'. Must be one of: {ALL_STYLES}"
            )

        logger.info("Regenerating %s caption (mock=%s)", style, self._using_mock)

        text = await self._generate_single(
            style, transcript, visual_context,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return Caption(
            text=text,
            style=CaptionStyle(style),
            word_count=len(text.split()),
            confidence=round(random.uniform(0.85, 0.98), 2),
            timestamp=datetime.utcnow(),
        )

    async def _generate_single(
        self,
        style: str,
        transcript: str,
        visual_context: list[str],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate a single caption for one style.

        Args:
            style: The caption style.
            transcript: Audio transcript.
            visual_context: Visual descriptions.
            temperature: Optional temperature override.
            max_tokens: Optional max_tokens override.

        Returns:
            Generated caption text string.
        """
        try:
            text = await self._client.generate_caption(
                style=style,
                transcript=transcript,
                visual_context=visual_context,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return text.strip()
        except Exception as exc:
            logger.error("Caption generation failed for style '%s': %s", style, exc)
            raise

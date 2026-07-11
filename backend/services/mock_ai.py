"""
CapturaAI — Mock AI fallback.

Generates plausible captions based on transcript and visual context keywords
when no Fireworks API key is available. Uses different templates for each
of the 4 caption styles to produce realistic-sounding results.
"""

import logging
import random
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Template pools for each style
# ---------------------------------------------------------------------------

_FORMAL_TEMPLATES = [
    "The footage presents {subject} engaged in {action}, showcasing a {mood} atmosphere against a {setting} backdrop. The visual composition emphasizes {detail}, reflecting a deliberate and measured approach to the subject matter.",
    "This video depicts {subject} in the process of {action}, set within {setting}. The sequence unfolds with clarity, highlighting {detail} and conveying a sense of {mood} throughout the presentation.",
    "A meticulously captured sequence features {subject} demonstrating {action} within {setting}. The visual narrative underscores {detail}, maintaining an objective and informative tone befitting the subject.",
    "The recording documents {subject} as they {action}, situated in {setting}. Notable elements include {detail}, contributing to an overall {mood} composition of professional caliber.",
    "An objective account of {subject} performing {action}, this footage offers a measured examination of the scene. Set in {setting}, the visual elements—particularly {detail}—lend the piece a distinctly {mood} quality.",
]

_SARCASTIC_TEMPLATES = [
    "Oh wonderful, another video of {subject} {action}. Truly groundbreaking content that humanity was desperately waiting for.",
    "Ah yes, {subject} decided today was the perfect day to {action}. The world will never be the same.",
    "Nothing says 'peak entertainment' quite like watching {subject} {action}. Oscar-worthy, really.",
    "Well, {subject} is out here {action} like it's the most important thing happening on the planet. Spoiler: it's not.",
    "Behold, {subject} {action}. If this doesn't go viral, I've officially lost all faith in the internet.",
]

_HUMOROUS_TECH_TEMPLATES = [
    "When your neural network finally converges and you celebrate by {action}—classic {subject} behavior. This is basically gradient descent in human form.",
    "POV: {subject} just pushed to production on a Friday and is now {action}. The CI/CD pipeline is crying somewhere.",
    "{subject} {action} with the confidence of a junior dev closing a ticket they didn't actually fix. This is the human equivalent of 'it works on my machine.'",
    "If {subject} {action} was a GitHub repo, it would have zero stars but 47 forks from confused bots. Peak open source energy.",
    "This is what happens when {subject} treats real life like a hackathon—{action} with the energy of someone who's been coding for 36 hours straight on Red Bull.",
]

_HUMOROUS_NON_TECH_TEMPLATES = [
    "{subject} out here {action} like they've got nothing better to do on a Tuesday. We've all been there, honestly.",
    "You know your day has peaked when you catch {subject} {action}. This is the content I signed up for.",
    "My spirit animal is definitely {subject} just casually {action}. No rush, no worries, just pure vibes.",
    "{subject} {action} and honestly, this has the same energy as eating cereal at 2 AM. No judgment here.",
    "If {subject} {action} doesn't perfectly sum up the human experience, I don't know what does. Somebody give this person an award.",
]

# Fallback keyword pools used when transcript/context are sparse
_SUBJECTS = [
    "a person", "someone", "an individual", "a figure", "the subject",
    "the presenter", "the creator", "a participant",
]
_ACTIONS = [
    "performing an activity", "interacting with objects", "moving through the scene",
    "demonstrating a technique", "exploring the environment", "going about their routine",
]
_SETTINGS = [
    "an indoor environment", "an outdoor setting", "a familiar space",
    "a well-lit area", "a casual setting", "a workspace",
]
_MOODS = [
    "calm", "energetic", "focused", "relaxed", "determined", "contemplative",
]
_DETAILS = [
    "subtle hand gestures", "careful movements", "dynamic composition",
    "natural lighting", "expressive body language", "the surrounding context",
]


def _extract_keywords(text: str) -> dict[str, str]:
    """
    Extract thematic keywords from transcript / visual context text.

    Returns a dictionary with 'subject', 'action', 'setting', 'mood', 'detail'.
    Falls back to random choices from default pools when text is too sparse.
    """
    text_lower = text.lower() if text else ""

    # Try to extract meaningful fragments
    subject = _pick_match(text_lower, [
        ("person", "a person"),
        ("people", "a group of people"),
        ("man", "a man"),
        ("woman", "a woman"),
        ("child", "a child"),
        ("animal", "an animal"),
        ("dog", "a dog"),
        ("cat", "a cat"),
        ("car", "a vehicle"),
    ], random.choice(_SUBJECTS))

    action = _pick_match(text_lower, [
        ("walk", "walking confidently"),
        ("run", "running with purpose"),
        ("talk", "talking animatedly"),
        ("cook", "cooking something interesting"),
        ("dance", "dancing enthusiastically"),
        ("play", "playing around"),
        ("work", "working diligently"),
        ("sit", "sitting contemplatively"),
        ("eat", "eating with gusto"),
        ("drive", "driving along"),
        ("sing", "singing their heart out"),
        ("read", "reading intently"),
        ("type", "typing away furiously"),
        ("laugh", "laughing heartily"),
        ("show", "showing something off"),
    ], random.choice(_ACTIONS))

    setting = _pick_match(text_lower, [
        ("outside", "an outdoor setting"),
        ("indoor", "an indoor space"),
        ("office", "a modern office"),
        ("kitchen", "a kitchen"),
        ("street", "a busy street"),
        ("park", "a park"),
        ("room", "a room"),
        ("garden", "a garden"),
        ("stage", "a stage"),
        ("studio", "a studio"),
    ], random.choice(_SETTINGS))

    mood = random.choice(_MOODS)
    detail = random.choice(_DETAILS)

    return {
        "subject": subject,
        "action": action,
        "setting": setting,
        "mood": mood,
        "detail": detail,
    }


def _pick_match(
    text: str,
    candidates: list[tuple[str, str]],
    default: str,
) -> str:
    """Pick first matching keyword or return default."""
    for keyword, value in candidates:
        if keyword in text:
            return value
    return default


class MockAI:
    """
    Fallback AI that generates plausible captions when no Fireworks API key
    is available. Uses template-based generation with keyword extraction
    from transcript and visual context.
    """

    def __init__(self):
        """Initialize the mock AI generator."""
        self._template_map: dict[str, list[str]] = {
            "formal": _FORMAL_TEMPLATES,
            "sarcastic": _SARCASTIC_TEMPLATES,
            "humorous_tech": _HUMOROUS_TECH_TEMPLATES,
            "humorous_non_tech": _HUMOROUS_NON_TECH_TEMPLATES,
        }

    async def generate_caption(
        self,
        style: str,
        transcript: str,
        visual_context: list[str],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate a mock caption for a given style.

        Args:
            style: One of 'formal', 'sarcastic', 'humorous_tech', 'humorous_non_tech'.
            transcript: The video transcript text.
            visual_context: List of visual descriptions.
            temperature: Ignored (kept for interface compatibility).
            max_tokens: Ignored (kept for interface compatibility).

        Returns:
            A plausible caption string.

        Raises:
            ValueError: If the style is not recognized.
        """
        if style not in self._template_map:
            raise ValueError(
                f"Unknown caption style '{style}'. "
                f"Must be one of: {list(self._template_map.keys())}"
            )

        # Combine transcript and visual context for keyword extraction
        combined_text = transcript or ""
        if visual_context:
            combined_text += " " + " ".join(visual_context)

        keywords = _extract_keywords(combined_text)
        templates = self._template_map[style]
        template = random.choice(templates)

        caption = template.format(**keywords)

        logger.info(
            "[MockAI] Generated %s caption (%d words): %s",
            style, len(caption.split()), caption[:80],
        )
        return caption

    async def generate_all(
        self,
        transcript: str,
        visual_context: list[str],
    ) -> dict[str, str]:
        """
        Generate captions for all 4 styles.

        Args:
            transcript: The video transcript text.
            visual_context: List of visual descriptions.

        Returns:
            Dictionary mapping style name to caption text.
        """
        results: dict[str, str] = {}
        for style in self._template_map:
            results[style] = await self.generate_caption(
                style, transcript, visual_context
            )
        return results

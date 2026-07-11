"""
CapturaAI Pydantic models for captions.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class CaptionStyle(str, Enum):
    """The four caption styles supported by CapturaAI."""
    FORMAL = "formal"
    SARCASTIC = "sarcastic"
    HUMOROUS_TECH = "humorous_tech"
    HUMOROUS_NON_TECH = "humorous_non_tech"


class Caption(BaseModel):
    """A single caption with metadata."""
    text: str = Field(..., description="The caption text")
    style: CaptionStyle = Field(..., description="Caption style")
    word_count: int = Field(default=0, description="Number of words in the caption")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="AI confidence score")
    timestamp: Optional[datetime] = Field(default=None, description="When the caption was generated")

    def model_post_init(self, __context) -> None:
        """Auto-compute word count after initialization."""
        if self.text and self.word_count == 0:
            self.word_count = len(self.text.split())


class CaptionSet(BaseModel):
    """All four caption styles for a single video."""
    video_id: str
    formal: Optional[Caption] = None
    sarcastic: Optional[Caption] = None
    humorous_tech: Optional[Caption] = None
    humorous_non_tech: Optional[Caption] = None
    transcript: str = Field(default="", description="Raw transcript from Whisper")
    visual_context: list[str] = Field(default_factory=list, description="Visual frame descriptions")
    transcript_segments: Optional[list[dict]] = Field(default=None, description="Whisper segments with timestamps")
    generated_at: Optional[datetime] = None

    def get_caption(self, style: CaptionStyle) -> Optional[Caption]:
        """Get a caption by style."""
        return getattr(self, style.value, None)

    def set_caption(self, style: CaptionStyle, caption: Caption) -> None:
        """Set a caption for a given style."""
        setattr(self, style.value, caption)

    def all_captions(self) -> dict[str, Optional[Caption]]:
        """Return all four captions as a dictionary."""
        return {
            CaptionStyle.FORMAL.value: self.formal,
            CaptionStyle.SARCASTIC.value: self.sarcastic,
            CaptionStyle.HUMOROUS_TECH.value: self.humorous_tech,
            CaptionStyle.HUMOROUS_NON_TECH.value: self.humorous_non_tech,
        }

    def is_complete(self) -> bool:
        """Check if all four captions have been generated."""
        return all(c is not None for c in self.all_captions().values())


class CaptionUpdateRequest(BaseModel):
    """Request body for updating/editing a caption."""
    text: str = Field(..., min_length=1, max_length=2000, description="New caption text")
    bottom_padding: Optional[float] = Field(default=None, ge=0.05, le=0.95, description="Optional dynamic offset from bottom")


class CaptionRegenerateRequest(BaseModel):
    """Optional body for caption regeneration with custom parameters."""
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=10, le=500)

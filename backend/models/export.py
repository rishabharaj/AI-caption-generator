"""
CapturaAI Pydantic models for export operations.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ExportRequest(BaseModel):
    """Request body specifying which items to include in a master ZIP export."""
    include_videos: bool = Field(default=True, description="Include all 4 styled videos")
    include_json: bool = Field(default=True, description="Include JSON captions file")
    include_srt: bool = Field(default=True, description="Include individual SRT files + combined")
    include_report: bool = Field(default=True, description="Include HTML report")
    include_transcript: bool = Field(default=True, description="Include original transcript text file")


class ExportResponse(BaseModel):
    """Response returned after an export is generated."""
    download_url: str = Field(..., description="URL to download the exported file")
    filename: str = Field(..., description="Suggested download filename")
    file_size: Optional[int] = Field(default=None, description="File size in bytes")
    content_type: str = Field(default="application/octet-stream")


class CaptionExportItem(BaseModel):
    """A single caption in the export JSON schema."""
    text: str
    style: str
    word_count: int
    confidence: float


class VideoExportInfo(BaseModel):
    """Video metadata in the export JSON schema."""
    filename: str
    duration: float
    has_audio: bool
    resolution: str
    fps: float


class CaptionExport(BaseModel):
    """
    Full JSON export schema matching the CapturaAI specification.

    Example output:
    {
        "project": "CapturaAI Export",
        "exported_at": "2026-07-11T08:45:00Z",
        "video": { ... },
        "captions": { ... }
    }
    """
    project: str = Field(default="CapturaAI Export")
    exported_at: datetime = Field(default_factory=datetime.utcnow)
    video: VideoExportInfo
    captions: dict[str, CaptionExportItem]

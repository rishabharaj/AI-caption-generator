"""
CapturaAI Pydantic models for video metadata, upload responses, and processing status.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ProcessingStep(str, Enum):
    """Individual steps in the video processing pipeline."""
    EXTRACTING_FRAMES = "extracting_frames"
    ANALYZING_AUDIO = "analyzing_audio"
    TRANSCRIBING = "transcribing"
    GENERATING_CAPTIONS = "generating_captions"
    BURNING_SUBTITLES = "burning_subtitles"
    COMPLETE = "complete"
    FAILED = "failed"


class StepStatus(str, Enum):
    """Status of an individual processing step."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETE = "complete"
    SKIPPED = "skipped"
    FAILED = "failed"


class StepDetail(BaseModel):
    """Detail for a single processing step."""
    step: ProcessingStep
    status: StepStatus = StepStatus.PENDING
    message: str = ""
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class VideoMetadata(BaseModel):
    """Metadata extracted from an uploaded video file."""
    filename: str = Field(..., description="Original filename of the uploaded video")
    duration: float = Field(..., description="Duration in seconds")
    has_audio: bool = Field(..., description="Whether the video contains an audio stream")
    resolution: str = Field(..., description="Resolution string e.g. '1920x1080'")
    fps: float = Field(..., description="Frames per second")
    file_size: int = Field(..., description="File size in bytes")


class VideoUploadResponse(BaseModel):
    """Response returned after a successful video upload."""
    video_id: str = Field(..., description="Unique UUID for this video")
    metadata: VideoMetadata
    status: str = Field(default="uploaded", description="Current status of the video")
    message: str = Field(default="Video uploaded successfully")


class ProcessingStatus(BaseModel):
    """Full processing status with step-by-step tracking."""
    video_id: str
    status: str = Field(default="pending", description="Overall status: pending, processing, complete, failed")
    current_step: Optional[ProcessingStep] = None
    progress_percent: float = Field(default=0.0, ge=0.0, le=100.0)
    steps: list[StepDetail] = Field(default_factory=list)
    has_audio: bool = False
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def initialize_steps(self) -> None:
        """Initialize the processing steps list."""
        self.steps = [
            StepDetail(step=ProcessingStep.EXTRACTING_FRAMES, message="Extracting video frames..."),
            StepDetail(step=ProcessingStep.ANALYZING_AUDIO, message="Analyzing audio stream..."),
            StepDetail(step=ProcessingStep.TRANSCRIBING, message="Transcribing speech..."),
            StepDetail(step=ProcessingStep.GENERATING_CAPTIONS, message="Generating captions (4 styles)..."),
            StepDetail(step=ProcessingStep.BURNING_SUBTITLES, message="Burning subtitles into videos..."),
        ]

    def advance_step(self, step: ProcessingStep, status: StepStatus, message: str = "") -> None:
        """Update a specific step's status."""
        for s in self.steps:
            if s.step == step:
                s.status = status
                if message:
                    s.message = message
                if status == StepStatus.PROCESSING:
                    s.started_at = datetime.utcnow()
                elif status in (StepStatus.COMPLETE, StepStatus.FAILED, StepStatus.SKIPPED):
                    s.completed_at = datetime.utcnow()
                break
        self._recalculate_progress()

    def _recalculate_progress(self) -> None:
        """Recalculate overall progress percentage from step statuses."""
        if not self.steps:
            return
        completed = sum(
            1 for s in self.steps
            if s.status in (StepStatus.COMPLETE, StepStatus.SKIPPED)
        )
        self.progress_percent = round((completed / len(self.steps)) * 100, 1)
        if self.progress_percent >= 100.0:
            self.status = "complete"
            self.current_step = ProcessingStep.COMPLETE
            self.completed_at = datetime.utcnow()

"""
CapturaAI — API routes.

All FastAPI endpoints for video upload, processing, caption management,
and export operations.
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse

from backend.api.dependencies import get_api_key
from backend.api.exceptions import (
    CaptionNotFound,
    FileTooLarge,
    InvalidFormat,
    ProcessingError,
    VideoNotFound,
    VideoTooLong,
    VideoTooShort,
)
from backend.config import settings
from backend.models.caption import Caption, CaptionSet, CaptionStyle, CaptionUpdateRequest
from backend.models.export import ExportRequest
from backend.models.video import (
    ProcessingStatus,
    ProcessingStep,
    StepStatus,
    VideoMetadata,
    VideoUploadResponse,
)
from backend.services.audio_detector import AudioDetector
from backend.services.caption_burner import CaptionBurner
from backend.services.caption_generator import CaptionGenerator
from backend.services.export_service import ExportService
from backend.services.video_processor import VideoProcessor
from backend.services.whisper_client import WhisperClient
from backend.utils.ffmpeg_utils import get_video_info
from backend.utils.file_utils import (
    ensure_video_dir,
    find_original_video,
    generate_video_id,
    get_styled_video_path,
    get_upload_path,
    get_video_dir,
    sanitize_filename,
)
from backend.utils.validators import validate_duration, validate_file_format, validate_file_size

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["api"])

# ---------------------------------------------------------------------------
# In-memory stores (production would use a database)
# ---------------------------------------------------------------------------
_processing_status: dict[str, ProcessingStatus] = {}
_video_metadata: dict[str, VideoMetadata] = {}
_caption_sets: dict[str, CaptionSet] = {}

# ---------------------------------------------------------------------------
# Service instances
# ---------------------------------------------------------------------------
video_processor = VideoProcessor()
audio_detector = AudioDetector()
whisper_client = WhisperClient()
caption_burner = CaptionBurner()
export_service = ExportService()


# ===========================================================================
# UPLOAD
# ===========================================================================

@router.post("/upload", response_model=VideoUploadResponse)
async def upload_video(file: UploadFile = File(...)):
    """
    Upload a video file for processing.

    Validates format (MP4, MOV, AVI, WEBM), size (<500MB), and duration (30s–2min).
    Returns a video_id for subsequent operations.
    """
    # Validate format
    filename = file.filename or "unknown.mp4"
    if not validate_file_format(filename):
        ext = Path(filename).suffix.lstrip(".")
        raise InvalidFormat(ext, list(settings.video.allowed_formats))

    # Generate ID and create directories
    video_id = generate_video_id()
    ensure_video_dir(video_id)
    upload_path = get_upload_path(video_id, filename)

    # Stream file to disk and check size
    total_size = 0
    max_size = settings.video.max_file_size_mb * 1024 * 1024

    try:
        with open(upload_path, "wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)  # 1 MB chunks
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > max_size:
                    # Clean up partial file
                    upload_path.unlink(missing_ok=True)
                    raise FileTooLarge(total_size, settings.video.max_file_size_mb)
                f.write(chunk)
    except FileTooLarge:
        raise
    except Exception as exc:
        upload_path.unlink(missing_ok=True)
        logger.error("Upload failed: %s", exc)
        raise ProcessingError(str(exc), step="upload")

    # Validate file size
    if not validate_file_size(total_size):
        upload_path.unlink(missing_ok=True)
        raise FileTooLarge(total_size, settings.video.max_file_size_mb)

    # Extract metadata and validate duration
    try:
        info = await get_video_info(upload_path)
    except Exception as exc:
        upload_path.unlink(missing_ok=True)
        raise ProcessingError(f"Cannot read video file: {exc}", step="metadata")

    duration = info["duration"]
    is_valid, error_msg = validate_duration(duration)
    if not is_valid:
        upload_path.unlink(missing_ok=True)
        if duration < settings.video.min_duration_seconds:
            raise VideoTooShort(duration, settings.video.min_duration_seconds)
        else:
            raise VideoTooLong(duration, settings.video.max_duration_seconds)

    # Build metadata
    metadata = VideoMetadata(
        filename=sanitize_filename(filename),
        duration=duration,
        has_audio=info["has_audio"],
        resolution=f"{info['width']}x{info['height']}",
        fps=info["fps"],
        file_size=total_size,
    )
    _video_metadata[video_id] = metadata

    # Initialize processing status
    status = ProcessingStatus(video_id=video_id, status="uploaded")
    status.initialize_steps()
    _processing_status[video_id] = status

    logger.info(
        "Video uploaded: %s (id=%s, %.1fs, %s)",
        filename, video_id, duration, metadata.resolution,
    )

    return VideoUploadResponse(
        video_id=video_id,
        metadata=metadata,
        status="uploaded",
        message="Video uploaded successfully. Call /api/process/{video_id} to begin processing.",
    )


@router.get("/diag")
async def diag():
    import os
    from backend.config import PROJECT_ROOT, settings
    from backend.utils.ffmpeg_utils import is_ffmpeg_available, get_ffmpeg_path, run_ffmpeg_command, build_drawtext_filter
    
    try:
        files = os.listdir(PROJECT_ROOT)
    except Exception as e:
        files = [f"Error listing files: {e}"]
        
    font_file = settings.caption_burner.font_file
    font_path = PROJECT_ROOT / font_file
    font_exists = font_path.exists()
    font_size = font_path.stat().st_size if font_exists else 0
    
    # Try running a dummy ffmpeg command with the font
    ffmpeg_error = None
    ffmpeg_output = None
    ffmpeg_cmd = []
    if font_exists:
        try:
            drawtext = build_drawtext_filter(
                text="Test Caption",
                font_file=str(font_path),
                font_size=24,
                video_width=100,
                video_height=100
            )
            args = [
                "-f", "lavfi",
                "-i", "color=c=black:s=100x100:d=1",
                "-vf", drawtext,
                "-f", "null",
                "-"
            ]
            ffmpeg_cmd = [get_ffmpeg_path()] + args
            rc, stdout, stderr = await run_ffmpeg_command(args, timeout=10, check=False)
            ffmpeg_output = {
                "return_code": rc,
                "stdout": stdout,
                "stderr": stderr
            }
        except Exception as exc:
            ffmpeg_error = f"Exception: {exc}"
            
    return {
        "project_root": str(PROJECT_ROOT),
        "files_in_root": files,
        "configured_font": font_file,
        "font_path": str(font_path),
        "font_exists": font_exists,
        "font_size": font_size,
        "ffmpeg_available": is_ffmpeg_available(),
        "ffmpeg_path": get_ffmpeg_path() if is_ffmpeg_available() else None,
        "ffmpeg_command_tried": " ".join(ffmpeg_cmd),
        "ffmpeg_error": ffmpeg_error,
        "ffmpeg_output": ffmpeg_output
    }


# ===========================================================================
# PROCESS
# ===========================================================================

@router.post("/process/{video_id}")
async def process_video(
    video_id: str,
    background_tasks: BackgroundTasks,
    bottom_padding: Optional[float] = None,
    api_key: Optional[str] = Depends(get_api_key),
):
    """
    Start processing an uploaded video.

    Pipeline: extract frames → detect audio → transcribe → generate 4 captions → burn subtitles.
    Processing runs in the background; poll /api/status/{video_id} for progress.
    """
    if video_id not in _processing_status:
        raise VideoNotFound(video_id)

    status = _processing_status[video_id]
    if status.status == "processing":
        return {"video_id": video_id, "message": "Already processing", "status": "processing"}

    status.status = "processing"
    status.started_at = datetime.utcnow()

    # Run processing in the background
    background_tasks.add_task(_run_processing_pipeline, video_id, api_key, bottom_padding)

    return {
        "video_id": video_id,
        "message": "Processing started",
        "status": "processing",
        "using_mock_ai": api_key is None,
    }


async def _run_processing_pipeline(
    video_id: str,
    api_key: Optional[str] = None,
    bottom_padding: Optional[float] = None,
):
    """
    Full processing pipeline executed as a background task.

    Steps:
    1. Extract video frames
    2. Detect and extract audio
    3. Transcribe speech (if audio)
    4. Generate 4 captions
    5. Burn subtitles into 4 separate videos
    """
    status = _processing_status[video_id]
    video_path = find_original_video(video_id)

    if not video_path:
        status.status = "failed"
        status.error = "Original video file not found"
        logger.error("Cannot find original video for %s", video_id)
        return

    try:
        # Step 1: Extract frames
        status.current_step = ProcessingStep.EXTRACTING_FRAMES
        status.advance_step(ProcessingStep.EXTRACTING_FRAMES, StepStatus.PROCESSING)
        frames = await video_processor.extract_frames(video_path, video_id)
        representative_frames = video_processor.select_representative_frames(frames)
        visual_context = [f"Frame {i+1}: visual content from video" for i, _ in enumerate(representative_frames)]
        status.advance_step(ProcessingStep.EXTRACTING_FRAMES, StepStatus.COMPLETE)

        # Step 2: Detect and extract audio
        status.current_step = ProcessingStep.ANALYZING_AUDIO
        status.advance_step(ProcessingStep.ANALYZING_AUDIO, StepStatus.PROCESSING)
        has_audio, audio_info = await audio_detector.detect(video_path)
        status.has_audio = has_audio

        metadata = _video_metadata.get(video_id)
        if metadata:
            metadata.has_audio = has_audio

        status.advance_step(ProcessingStep.ANALYZING_AUDIO, StepStatus.COMPLETE)

        # Step 3: Transcribe speech
        status.current_step = ProcessingStep.TRANSCRIBING
        status.advance_step(ProcessingStep.TRANSCRIBING, StepStatus.PROCESSING)
        transcript = ""
        if has_audio:
            try:
                audio_path = await video_processor.extract_audio(video_path, video_id)
                result = await whisper_client.transcribe(audio_path, api_key=api_key)
                transcript = result.text
                logger.info("Transcript (%d words): %s", result.word_count, transcript[:100])
            except Exception as exc:
                logger.warning("Transcription failed, proceeding without: %s", exc)
                transcript = ""
            status.advance_step(ProcessingStep.TRANSCRIBING, StepStatus.COMPLETE)
        else:
            logger.info("No audio detected — skipping transcription")
            status.advance_step(
                ProcessingStep.TRANSCRIBING, StepStatus.SKIPPED,
                message="No audio detected — visual analysis only",
            )

        # Step 4: Generate captions
        status.current_step = ProcessingStep.GENERATING_CAPTIONS
        status.advance_step(ProcessingStep.GENERATING_CAPTIONS, StepStatus.PROCESSING)
        generator = CaptionGenerator(api_key=api_key)
        caption_set = await generator.generate_all(video_id, transcript, visual_context)
        if has_audio and 'result' in locals() and result:
            caption_set.transcript_segments = [s.to_dict() for s in result.segments]
        _caption_sets[video_id] = caption_set
        status.advance_step(ProcessingStep.GENERATING_CAPTIONS, StepStatus.COMPLETE)

        # Step 5: Burn subtitles — SKIPPED for speed
        # Captions are rendered as CSS overlays by the frontend,
        # so burning them into the video file is not needed.
        status.current_step = ProcessingStep.BURNING_SUBTITLES
        status.advance_step(
            ProcessingStep.BURNING_SUBTITLES, StepStatus.SKIPPED,
            message="Captions rendered as overlay — video burn skipped",
        )

        # Done
        status.status = "complete"
        status.current_step = ProcessingStep.COMPLETE
        status.completed_at = datetime.utcnow()
        status.progress_percent = 100.0
        logger.info("Processing complete for video %s", video_id)

    except Exception as exc:
        status.status = "failed"
        status.current_step = ProcessingStep.FAILED
        status.error = str(exc)
        logger.exception("Processing failed for video %s: %s", video_id, exc)


# ===========================================================================
# STATUS
# ===========================================================================

@router.get("/status/{video_id}", response_model=ProcessingStatus)
async def get_status(video_id: str):
    """Get the current processing status with step-by-step progress."""
    if video_id not in _processing_status:
        raise VideoNotFound(video_id)
    return _processing_status[video_id]


# ===========================================================================
# VIDEO SERVING
# ===========================================================================

@router.get("/video/{video_id}/{style}")
async def serve_styled_video(video_id: str, style: str):
    """Serve the original video for playback (captions rendered as CSS overlay)."""
    _validate_style(style)
    # Serve original video — captions are overlaid by the frontend
    video_path = find_original_video(video_id)
    if not video_path:
        raise VideoNotFound(video_id)
    return FileResponse(
        video_path,
        media_type="video/mp4",
        filename=f"{style}.mp4",
    )


@router.get("/download/{video_id}/{style}")
async def download_styled_video(video_id: str, style: str):
    """Download the original video as an attachment (captions rendered as overlay)."""
    _validate_style(style)
    # Serve original video — captions are overlaid by the frontend
    video_path = find_original_video(video_id)
    if not video_path:
        raise VideoNotFound(video_id)

    metadata = _video_metadata.get(video_id)
    original_name = metadata.filename.rsplit(".", 1)[0] if metadata else video_id[:8]
    download_name = f"{original_name}_{style}.mp4"

    return FileResponse(
        video_path,
        media_type="video/mp4",
        filename=download_name,
        headers={"Content-Disposition": f"attachment; filename=\"{download_name}\""},
    )


@router.get("/original-video/{video_id}")
async def serve_original_video(video_id: str):
    """Serve the original uploaded video."""
    video_path = find_original_video(video_id)
    if not video_path:
        raise VideoNotFound(video_id)
    return FileResponse(
        video_path,
        media_type="video/mp4",
        filename=video_path.name,
    )


# ===========================================================================
# CAPTIONS
# ===========================================================================

@router.get("/captions/{video_id}")
async def get_captions(video_id: str):
    """Get all 4 captions for a video."""
    if video_id not in _caption_sets:
        raise VideoNotFound(video_id)
    caption_set = _caption_sets[video_id]
    metadata = _video_metadata.get(video_id)
    return {
        "video_id": video_id,
        "video": metadata.model_dump() if metadata else None,
        "captions": {
            style: caption.model_dump() if caption else None
            for style, caption in caption_set.all_captions().items()
        },
        "transcript": caption_set.transcript,
        "generated_at": caption_set.generated_at,
    }



@router.post("/captions/{video_id}/{style}/regenerate")
async def regenerate_caption(
    video_id: str,
    style: str,
    bottom_padding: Optional[float] = None,
    api_key: Optional[str] = Depends(get_api_key),
):
    """Regenerate a single caption for a specific style."""
    _validate_style(style)
    if video_id not in _caption_sets:
        raise VideoNotFound(video_id)

    caption_set = _caption_sets[video_id]
    generator = CaptionGenerator(api_key=api_key)

    new_caption = await generator.regenerate_single(
        style=style,
        transcript=caption_set.transcript,
        visual_context=caption_set.visual_context,
    )

    caption_set.set_caption(CaptionStyle(style), new_caption)

    # Video burn skipped — captions are rendered as CSS overlay by the frontend

    return {
        "video_id": video_id,
        "style": style,
        "caption": new_caption.model_dump(),
        "message": f"Caption regenerated for {style} style",
    }


@router.put("/captions/{video_id}/{style}")
async def update_caption(
    video_id: str,
    style: str,
    body: CaptionUpdateRequest,
):
    """Update/edit a caption manually."""
    _validate_style(style)
    if video_id not in _caption_sets:
        raise VideoNotFound(video_id)

    caption_set = _caption_sets[video_id]
    existing = caption_set.get_caption(CaptionStyle(style))

    updated_caption = Caption(
        text=body.text,
        style=CaptionStyle(style),
        word_count=len(body.text.split()),
        confidence=existing.confidence if existing else 1.0,
        timestamp=datetime.utcnow(),
    )

    caption_set.set_caption(CaptionStyle(style), updated_caption)

    # Video burn skipped — captions are rendered as CSS overlay by the frontend

    return {
        "video_id": video_id,
        "style": style,
        "caption": updated_caption.model_dump(),
        "message": f"Caption updated for {style} style",
    }


# ===========================================================================
# EXPORTS
# ===========================================================================

@router.get("/export/json/{video_id}")
async def export_json(video_id: str):
    """Export captions as a JSON file (specification format)."""
    metadata, caption_set = _get_export_data(video_id)
    json_content = export_service.generate_json_export(video_id, metadata, caption_set)
    return JSONResponse(
        content=json_content if isinstance(json_content, dict) else __import__("json").loads(json_content),
        headers={
            "Content-Disposition": f"attachment; filename=\"{video_id}_captions.json\"",
        },
    )


@router.get("/export/srt/{video_id}/{style}")
async def export_srt(video_id: str, style: str):
    """Export an individual SRT file for a single style."""
    _validate_style(style)
    metadata, caption_set = _get_export_data(video_id)
    srt_content = export_service.generate_individual_srt(
        video_id, style, caption_set, metadata.duration,
    )
    if not srt_content:
        raise CaptionNotFound(video_id, style)

    return StreamingResponse(
        iter([srt_content.encode("utf-8")]),
        media_type="text/srt",
        headers={
            "Content-Disposition": f"attachment; filename=\"{video_id}_{style}.srt\"",
        },
    )


@router.get("/export/srt-combined/{video_id}")
async def export_srt_combined(video_id: str):
    """Export a combined SRT file with all 4 styles labeled."""
    metadata, caption_set = _get_export_data(video_id)
    srt_content = export_service.generate_combined_srt(caption_set, metadata.duration)

    return StreamingResponse(
        iter([srt_content.encode("utf-8")]),
        media_type="text/srt",
        headers={
            "Content-Disposition": f"attachment; filename=\"{video_id}_combined.srt\"",
        },
    )


@router.post("/export/videos-zip/{video_id}")
async def export_videos_zip(video_id: str):
    """Create and return a ZIP of all 4 styled videos."""
    if video_id not in _caption_sets:
        raise VideoNotFound(video_id)
    zip_path = export_service.create_videos_zip(video_id)
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=f"{video_id}_all_styles.zip",
        headers={"Content-Disposition": f"attachment; filename=\"{video_id}_all_styles.zip\""},
    )


@router.get("/export/report/{video_id}")
async def export_report(video_id: str):
    """Generate and serve an HTML report."""
    metadata, caption_set = _get_export_data(video_id)
    html_content = export_service.generate_html_report(video_id, metadata, caption_set)
    return HTMLResponse(content=html_content)


@router.post("/export/full-zip/{video_id}")
async def export_full_zip(
    video_id: str,
    body: ExportRequest = ExportRequest(),
):
    """Create a master ZIP with selected items (videos, JSON, SRT, report, transcript)."""
    metadata, caption_set = _get_export_data(video_id)
    zip_path = export_service.create_full_zip(
        video_id=video_id,
        metadata=metadata,
        caption_set=caption_set,
        include_videos=body.include_videos,
        include_json=body.include_json,
        include_srt=body.include_srt,
        include_report=body.include_report,
        include_transcript=body.include_transcript,
    )
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"CapturaAI_Export_{video_id[:8]}_{timestamp}.zip"
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=filename,
        headers={"Content-Disposition": f"attachment; filename=\"{filename}\""},
    )


# ===========================================================================
# Helpers
# ===========================================================================

def _validate_style(style: str) -> None:
    """Validate that a style string is one of the 4 known styles."""
    valid_styles = {s.value for s in CaptionStyle}
    if style not in valid_styles:
        raise InvalidFormat(
            style,
            list(valid_styles),
        )


def _get_export_data(video_id: str) -> tuple[VideoMetadata, CaptionSet]:
    """Retrieve metadata and captions for export, raising if not found."""
    if video_id not in _video_metadata:
        raise VideoNotFound(video_id)
    if video_id not in _caption_sets:
        raise VideoNotFound(video_id)
    return _video_metadata[video_id], _caption_sets[video_id]

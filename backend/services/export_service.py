"""
CapturaAI — Export service.

Handles JSON, SRT, ZIP, and HTML report generation for video captions.
"""

import base64
import json
import logging
import zipfile
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Optional

from backend.config import settings
from backend.models.caption import CaptionSet, CaptionStyle
from backend.models.export import CaptionExport, CaptionExportItem, VideoExportInfo
from backend.models.video import VideoMetadata
from backend.utils.file_utils import (
    get_export_dir,
    get_output_dir,
    get_styled_video_path,
    find_original_video,
)

logger = logging.getLogger(__name__)

# Map of style keys to SRT display labels
_SRT_LABELS: dict[str, str] = {
    "formal": "FORMAL",
    "sarcastic": "SARCASTIC",
    "humorous_tech": "HUMOR-TECH",
    "humorous_non_tech": "HUMOR-NONTECH",
}

_STYLE_COLORS: dict[str, str] = {
    "formal": "#60a5fa",
    "sarcastic": "#f472b6",
    "humorous_tech": "#a78bfa",
    "humorous_non_tech": "#34d399",
}


class ExportService:
    """
    Generates exports in various formats: JSON, SRT, ZIP, and HTML reports.
    """

    # ------------------------------------------------------------------
    # JSON Export
    # ------------------------------------------------------------------

    def generate_json_export(
        self,
        video_id: str,
        metadata: VideoMetadata,
        caption_set: CaptionSet,
    ) -> str:
        """
        Generate a JSON export matching the specification format.

        Args:
            video_id: Unique video identifier.
            metadata: Video metadata.
            caption_set: All 4 captions.

        Returns:
            JSON string.
        """
        captions_dict: dict[str, CaptionExportItem] = {}
        for style_name, caption in caption_set.all_captions().items():
            if caption:
                captions_dict[style_name] = CaptionExportItem(
                    text=caption.text,
                    style=caption.style.value,
                    word_count=caption.word_count,
                    confidence=caption.confidence,
                )

        export = CaptionExport(
            project="CapturaAI Export",
            exported_at=datetime.utcnow(),
            video=VideoExportInfo(
                filename=metadata.filename,
                duration=metadata.duration,
                has_audio=metadata.has_audio,
                resolution=metadata.resolution,
                fps=metadata.fps,
            ),
            captions=captions_dict,
        )

        return export.model_dump_json(indent=settings.export.json_indent)

    def save_json_export(
        self,
        video_id: str,
        metadata: VideoMetadata,
        caption_set: CaptionSet,
    ) -> Path:
        """
        Generate and save JSON export to disk.

        Returns:
            Path to the saved JSON file.
        """
        export_dir = get_export_dir(video_id)
        export_dir.mkdir(parents=True, exist_ok=True)

        json_content = self.generate_json_export(video_id, metadata, caption_set)
        output_path = export_dir / f"{video_id}_captions.json"
        output_path.write_text(json_content, encoding="utf-8")

        logger.info("JSON export saved to %s", output_path)
        return output_path

    # ------------------------------------------------------------------
    # SRT Export
    # ------------------------------------------------------------------

    def generate_srt(
        self,
        caption_text: str,
        duration: float,
        style_label: Optional[str] = None,
    ) -> str:
        """
        Generate SRT content for a single caption.

        The caption is treated as a single subtitle spanning the full video.

        Args:
            caption_text: The caption text.
            duration: Video duration in seconds.
            style_label: Optional style label prefix (e.g. "[FORMAL]").

        Returns:
            SRT formatted string.
        """
        start_time = _format_srt_time(0.0)
        end_time = _format_srt_time(duration)

        text = caption_text
        if style_label:
            text = f"[{style_label}] {text}"

        return f"1\n{start_time} --> {end_time}\n{text}\n"

    def generate_individual_srt(
        self,
        video_id: str,
        style: str,
        caption_set: CaptionSet,
        duration: float,
    ) -> str:
        """
        Generate SRT for a single style.

        Args:
            video_id: Video identifier.
            style: Caption style name.
            caption_set: The caption set.
            duration: Video duration in seconds.

        Returns:
            SRT content string.
        """
        caption = caption_set.get_caption(CaptionStyle(style))
        if not caption:
            return ""
        return self.generate_srt(caption.text, duration)

    def generate_combined_srt(
        self,
        caption_set: CaptionSet,
        duration: float,
    ) -> str:
        """
        Generate a combined SRT with all 4 styles labeled.

        Format from spec:
        1
        00:00:00,000 --> 00:00:05,000
        [FORMAL] A person demonstrates...

        Args:
            caption_set: The caption set.
            duration: Video duration in seconds.

        Returns:
            Combined SRT content string.
        """
        start_time = _format_srt_time(0.0)
        end_time = _format_srt_time(duration)

        entries: list[str] = []
        idx = 1

        for style_val, label in _SRT_LABELS.items():
            caption = caption_set.get_caption(CaptionStyle(style_val))
            if caption:
                entry = f"{idx}\n{start_time} --> {end_time}\n[{label}] {caption.text}\n"
                entries.append(entry)
                idx += 1

        return "\n".join(entries)

    def save_srt_files(
        self,
        video_id: str,
        caption_set: CaptionSet,
        duration: float,
    ) -> dict[str, Path]:
        """
        Save individual and combined SRT files.

        Returns:
            Dictionary mapping 'style' and 'combined' to file paths.
        """
        export_dir = get_export_dir(video_id)
        export_dir.mkdir(parents=True, exist_ok=True)
        results: dict[str, Path] = {}

        for style_val in _SRT_LABELS:
            srt = self.generate_individual_srt(video_id, style_val, caption_set, duration)
            if srt:
                path = export_dir / f"{video_id}_{style_val}.srt"
                path.write_text(srt, encoding="utf-8")
                results[style_val] = path

        combined = self.generate_combined_srt(caption_set, duration)
        combined_path = export_dir / f"{video_id}_combined.srt"
        combined_path.write_text(combined, encoding="utf-8")
        results["combined"] = combined_path

        logger.info("Saved %d SRT files for video %s", len(results), video_id)
        return results

    # ------------------------------------------------------------------
    # ZIP Exports
    # ------------------------------------------------------------------

    def create_videos_zip(self, video_id: str) -> Path:
        """
        Create a ZIP containing all 4 styled videos.

        Args:
            video_id: Video identifier.

        Returns:
            Path to the created ZIP file.
        """
        export_dir = get_export_dir(video_id)
        export_dir.mkdir(parents=True, exist_ok=True)
        zip_path = export_dir / f"{video_id}_all_styles.zip"

        output_dir = get_output_dir(video_id)

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for style_val in _SRT_LABELS:
                video_file = get_styled_video_path(video_id, style_val)
                if video_file.exists():
                    zf.write(video_file, f"{style_val}.mp4")
                    logger.debug("Added %s to ZIP", video_file.name)

        logger.info("Videos ZIP created: %s (%.1f MB)", zip_path, zip_path.stat().st_size / (1024*1024))
        return zip_path

    def create_full_zip(
        self,
        video_id: str,
        metadata: VideoMetadata,
        caption_set: CaptionSet,
        include_videos: bool = True,
        include_json: bool = True,
        include_srt: bool = True,
        include_report: bool = True,
        include_transcript: bool = True,
    ) -> Path:
        """
        Create a master ZIP with selected export items.

        Args:
            video_id: Video identifier.
            metadata: Video metadata.
            caption_set: All captions.
            include_videos: Include styled video files.
            include_json: Include JSON captions.
            include_srt: Include SRT files.
            include_report: Include HTML report.
            include_transcript: Include transcript text.

        Returns:
            Path to the master ZIP file.
        """
        export_dir = get_export_dir(video_id)
        export_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        zip_path = export_dir / f"CapturaAI_Export_{video_id[:8]}_{timestamp}.zip"

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # Videos
            if include_videos:
                for style_val in _SRT_LABELS:
                    video_file = get_styled_video_path(video_id, style_val)
                    if video_file.exists():
                        zf.write(video_file, f"videos/{style_val}.mp4")

            # JSON
            if include_json:
                json_content = self.generate_json_export(video_id, metadata, caption_set)
                zf.writestr("captions.json", json_content)

            # SRT files
            if include_srt:
                for style_val, label in _SRT_LABELS.items():
                    srt = self.generate_individual_srt(
                        video_id, style_val, caption_set, metadata.duration,
                    )
                    if srt:
                        zf.writestr(f"srt/{style_val}.srt", srt)
                combined = self.generate_combined_srt(caption_set, metadata.duration)
                zf.writestr("srt/combined.srt", combined)

            # HTML Report
            if include_report:
                report_html = self.generate_html_report(video_id, metadata, caption_set)
                zf.writestr("report.html", report_html)

            # Transcript
            if include_transcript and caption_set.transcript:
                zf.writestr("transcript.txt", caption_set.transcript)

        logger.info(
            "Master ZIP created: %s (%.1f MB)",
            zip_path, zip_path.stat().st_size / (1024*1024),
        )
        return zip_path

    # ------------------------------------------------------------------
    # HTML Report
    # ------------------------------------------------------------------

    def generate_html_report(
        self,
        video_id: str,
        metadata: VideoMetadata,
        caption_set: CaptionSet,
    ) -> str:
        """
        Generate a printable HTML report with video metadata and captions.

        Args:
            video_id: Video identifier.
            metadata: Video metadata.
            caption_set: All captions.

        Returns:
            HTML content string.
        """
        # Build caption cards HTML
        caption_cards = ""
        for style_val, label in _SRT_LABELS.items():
            caption = caption_set.get_caption(CaptionStyle(style_val))
            color = _STYLE_COLORS.get(style_val, "#ffffff")
            text = caption.text if caption else "Not generated"
            word_count = caption.word_count if caption else 0
            confidence = caption.confidence if caption else 0.0

            caption_cards += f"""
            <div class="caption-card" style="border-left: 4px solid {color};">
                <div class="caption-header">
                    <span class="badge" style="background: {color}; color: #000;">{label}</span>
                    <span class="meta">{word_count} words · {confidence:.0%} confidence</span>
                </div>
                <p class="caption-text">{text}</p>
            </div>
            """

        # Build thumbnail grid from styled videos
        thumbnail_grid = ""
        for style_val, label in _SRT_LABELS.items():
            color = _STYLE_COLORS.get(style_val, "#ffffff")
            thumbnail_grid += f"""
            <div class="thumb-card">
                <div class="thumb-label" style="background: {color}; color: #000;">{label}</div>
                <div class="thumb-placeholder">🎬</div>
            </div>
            """

        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        audio_badge = "✅ Audio Detected" if metadata.has_audio else "🔇 No Audio — Visual Only"

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CapturaAI Export Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #0a0a0f;
            color: #e8e8f0;
            padding: 40px;
            line-height: 1.6;
        }}
        .container {{ max-width: 900px; margin: 0 auto; }}
        .header {{
            text-align: center;
            padding: 32px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            margin-bottom: 32px;
        }}
        .header h1 {{ font-size: 2rem; font-weight: 700; letter-spacing: -0.02em; }}
        .header .subtitle {{ color: #8b8b9e; margin-top: 8px; }}
        .section {{ margin-bottom: 32px; }}
        .section h2 {{
            font-size: 1.2rem;
            font-weight: 600;
            margin-bottom: 16px;
            color: #a78bfa;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: rgba(255,255,255,0.04);
            border-radius: 12px;
            overflow: hidden;
        }}
        th, td {{
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.06);
        }}
        th {{ color: #8b8b9e; font-weight: 500; font-size: 0.875rem; text-transform: uppercase; }}
        td {{ color: #e8e8f0; }}
        .caption-card {{
            background: rgba(255,255,255,0.04);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 16px;
        }}
        .caption-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }}
        .badge {{
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }}
        .meta {{ color: #8b8b9e; font-size: 0.8rem; }}
        .caption-text {{ font-size: 1rem; line-height: 1.7; }}
        .thumb-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
        }}
        .thumb-card {{
            background: rgba(255,255,255,0.04);
            border-radius: 8px;
            padding: 12px;
            text-align: center;
        }}
        .thumb-label {{
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.7rem;
            font-weight: 600;
            display: inline-block;
            margin-bottom: 8px;
        }}
        .thumb-placeholder {{
            font-size: 2rem;
            opacity: 0.5;
            padding: 20px;
        }}
        .footer {{
            text-align: center;
            padding: 24px 0;
            border-top: 1px solid rgba(255,255,255,0.1);
            color: #8b8b9e;
            font-size: 0.8rem;
        }}
        .print-btn {{
            display: inline-block;
            background: #6366f1;
            color: white;
            padding: 10px 24px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.9rem;
            margin-top: 16px;
        }}
        @media print {{
            body {{ background: white; color: #1a1a2e; padding: 20px; }}
            .print-btn {{ display: none; }}
            .caption-card {{ border: 1px solid #ddd; }}
            table {{ border: 1px solid #ddd; }}
            th, td {{ border: 1px solid #ddd; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎬 CapturaAI Export Report</h1>
            <p class="subtitle">Generated on {timestamp}</p>
        </div>

        <div class="section">
            <h2>📹 Video Metadata</h2>
            <table>
                <tr><th>Filename</th><td>{metadata.filename}</td></tr>
                <tr><th>Duration</th><td>{metadata.duration:.1f}s</td></tr>
                <tr><th>Resolution</th><td>{metadata.resolution}</td></tr>
                <tr><th>FPS</th><td>{metadata.fps}</td></tr>
                <tr><th>File Size</th><td>{metadata.file_size / (1024*1024):.1f} MB</td></tr>
                <tr><th>Audio</th><td>{audio_badge}</td></tr>
            </table>
        </div>

        <div class="section">
            <h2>🎞️ Styled Video Previews</h2>
            <div class="thumb-grid">
                {thumbnail_grid}
            </div>
        </div>

        <div class="section">
            <h2>💬 Generated Captions</h2>
            {caption_cards}
        </div>

        <div class="footer">
            <p>CapturaAI — 4-Style Video Captioning Platform</p>
            <p>Video ID: {video_id}</p>
            <button class="print-btn" onclick="window.print()">🖨️ Print to PDF</button>
        </div>
    </div>
</body>
</html>"""

        return html

    def save_html_report(
        self,
        video_id: str,
        metadata: VideoMetadata,
        caption_set: CaptionSet,
    ) -> Path:
        """
        Generate and save HTML report to disk.

        Returns:
            Path to the saved HTML file.
        """
        export_dir = get_export_dir(video_id)
        export_dir.mkdir(parents=True, exist_ok=True)

        html = self.generate_html_report(video_id, metadata, caption_set)
        output_path = export_dir / f"{video_id}_report.html"
        output_path.write_text(html, encoding="utf-8")

        logger.info("HTML report saved to %s", output_path)
        return output_path


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _format_srt_time(seconds: float) -> str:
    """
    Format seconds as SRT timestamp (HH:MM:SS,mmm).

    Args:
        seconds: Time in seconds.

    Returns:
        Formatted SRT time string.
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

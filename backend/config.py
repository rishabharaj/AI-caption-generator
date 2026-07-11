"""
CapturaAI Configuration Loader.

Loads application configuration from config.yaml with sensible defaults.
Uses pathlib for cross-platform path handling.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

# Project root is the parent of the backend directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.yaml"


@dataclass
class ServerConfig:
    """Web server configuration."""
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True
    workers: int = 1


@dataclass
class VideoConfig:
    """Video processing constraints."""
    min_duration_seconds: float = 30.0
    max_duration_seconds: float = 120.0
    max_file_size_mb: int = 500
    allowed_formats: list[str] = field(
        default_factory=lambda: ["mp4", "mov", "avi", "webm"]
    )
    frames_per_second: int = 1
    representative_frames: int = 10
    frame_scale_width: int = 480


@dataclass
class ModelConfig:
    """AI model configuration."""
    use_fine_tuned: bool = False
    fine_tuned_model_id: str = ""
    base_model: str = "accounts/fireworks/models/llama-v3p1-8b-instruct"
    max_tokens: int = 150
    temperature: float = 0.8


@dataclass
class FireworksConfig:
    """Fireworks AI API configuration."""
    base_url: str = "https://api.fireworks.ai/inference/v1"
    timeout_seconds: int = 30
    max_retries: int = 3
    retry_delay_seconds: float = 1.0


@dataclass
class WhisperConfig:
    """OpenAI Whisper configuration."""
    model_name: str = "base"
    language: Optional[str] = None
    sample_rate: int = 16000


@dataclass
class CaptionBurnerConfig:
    """Caption burning (ffmpeg drawtext) configuration."""
    font_file: str = "Inter-Bold.ttf"
    font_size: int = 24
    font_color: str = "white"
    border_width: int = 2
    border_color: str = "black"
    background_opacity: float = 0.5
    bottom_padding_percent: float = 0.10
    max_text_width_percent: float = 0.90


@dataclass
class ExportConfig:
    """Export/download configuration."""
    json_indent: int = 2
    report_title: str = "CapturaAI Export Report"


@dataclass
class StorageConfig:
    """File storage paths."""
    temp_dir: str = "temp"
    upload_dir: str = "uploads"
    output_dir: str = "outputs"
    frames_dir: str = "frames"
    audio_dir: str = "audio"


@dataclass
class AppConfig:
    """Top-level application configuration."""
    app_name: str = "CapturaAI"
    app_version: str = "1.0.0"
    debug: bool = True
    server: ServerConfig = field(default_factory=ServerConfig)
    video: VideoConfig = field(default_factory=VideoConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    fireworks: FireworksConfig = field(default_factory=FireworksConfig)
    whisper: WhisperConfig = field(default_factory=WhisperConfig)
    caption_burner: CaptionBurnerConfig = field(default_factory=CaptionBurnerConfig)
    export: ExportConfig = field(default_factory=ExportConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)

    @property
    def temp_path(self) -> Path:
        """Absolute path to the temp directory."""
        return PROJECT_ROOT / self.storage.temp_dir

    @property
    def frontend_path(self) -> Path:
        """Absolute path to the frontend directory."""
        return PROJECT_ROOT / "frontend"


def _merge_dict(base: dict, override: dict) -> dict:
    """Recursively merge override dict into base dict."""
    merged = base.copy()
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _merge_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


def _dict_to_config(data: dict) -> AppConfig:
    """Convert a raw dictionary to an AppConfig dataclass instance."""
    return AppConfig(
        app_name=data.get("app_name", "CapturaAI"),
        app_version=data.get("app_version", "1.0.0"),
        debug=data.get("debug", True),
        server=ServerConfig(**data.get("server", {})),
        video=VideoConfig(**data.get("video", {})),
        model=ModelConfig(**data.get("model", {})),
        fireworks=FireworksConfig(**data.get("fireworks", {})),
        whisper=WhisperConfig(**data.get("whisper", {})),
        caption_burner=CaptionBurnerConfig(**data.get("caption_burner", {})),
        export=ExportConfig(**data.get("export", {})),
        storage=StorageConfig(**data.get("storage", {})),
    )


def load_config(config_path: Optional[Path] = None) -> AppConfig:
    """
    Load configuration from a YAML file.

    Falls back to default values if the config file is missing or unreadable.

    Args:
        config_path: Optional path to the config file. Defaults to project root config.yaml.

    Returns:
        AppConfig instance with loaded or default values.
    """
    path = config_path or CONFIG_PATH

    if path.exists() and path.is_file():
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
            logger.info("Loaded configuration from %s", path)
            return _dict_to_config(raw)
        except yaml.YAMLError as exc:
            logger.warning("Failed to parse config file %s: %s. Using defaults.", path, exc)
        except Exception as exc:
            logger.warning("Error reading config file %s: %s. Using defaults.", path, exc)
    else:
        logger.info("Config file not found at %s. Using default configuration.", path)

    return AppConfig()


# Module-level singleton – import `settings` from anywhere
settings = load_config()

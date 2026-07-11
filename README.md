# 🎬 CapturaAI — 4-Style Video Captioning Platform

<p align="center">
  <strong>Generate 4 distinct caption styles for any video and compare them side-by-side</strong>
</p>

---

## ✨ Features

- **4-Quadrant Split View** — Watch the same video with 4 different caption styles burned in, playing in perfect sync
- **4 Caption Styles** — Formal, Sarcastic, Humorous-Tech, and Humorous-NonTech
- **Audio + Visual Analysis** — Uses Whisper for transcription + frame analysis for context
- **No Audio? No Problem** — Falls back to visual-only analysis for mute videos
- **Stunning Dark UI** — Glassmorphism design with smooth animations and micro-interactions
- **Export Everything** — JSON, SRT, individual/bundled MP4s, HTML reports, master ZIP
- **Mock AI Fallback** — Works without an API key using intelligent template-based generation
- **Fine-tuning Ready** — Pipeline for training on MSR-VTT and ActivityNet datasets

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **ffmpeg** installed and available in PATH
  - Windows: `winget install ffmpeg` or download from [ffmpeg.org](https://ffmpeg.org/download.html)
  - macOS: `brew install ffmpeg`
  - Linux: `sudo apt install ffmpeg`

### Installation

```bash
# Clone the repository
cd Vdcap

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Running the App

```bash
# Start the server
python -m backend.main
```

The app will be available at **http://localhost:8000**

### Configuration

1. Open the app in your browser
2. Enter your **Fireworks AI API key** (starts with `fw_`) in the header input
3. Upload a video (30s - 2min, up to 500MB)
4. Watch the magic happen! ✨

> **No API key?** The app will automatically use Mock AI to generate plausible captions.

## 📂 Project Structure

```
Vdcap/
├── backend/
│   ├── main.py                 # FastAPI application entry
│   ├── config.py               # Config loader (YAML)
│   ├── api/
│   │   ├── routes.py           # All FastAPI endpoints
│   │   ├── dependencies.py     # API key validation
│   │   └── exceptions.py       # Custom error handlers
│   ├── services/
│   │   ├── video_processor.py  # ffmpeg frame + audio extraction
│   │   ├── audio_detector.py   # Detect if video has audio
│   │   ├── whisper_client.py   # OpenAI Whisper integration
│   │   ├── caption_generator.py# 4-style prompt engine
│   │   ├── fireworks_client.py # Fireworks API wrapper
│   │   ├── mock_ai.py          # Fallback mock AI
│   │   ├── caption_burner.py   # ffmpeg drawtext overlay
│   │   └── export_service.py   # ZIP, JSON, SRT generation
│   ├── models/
│   │   ├── video.py            # Pydantic video models
│   │   ├── caption.py          # Pydantic caption models
│   │   └── export.py           # Pydantic export models
│   ├── utils/
│   │   ├── ffmpeg_utils.py     # ffmpeg command builders
│   │   ├── file_utils.py       # Temp file management
│   │   └── validators.py       # Duration, size validation
│   └── train_captioner.py      # Fine-tuning pipeline
├── frontend/
│   ├── index.html              # Main dashboard
│   ├── style.css               # Glassmorphism design system
│   ├── main.js                 # Sync playback, API calls
│   ├── animations.js           # Loading effects, particles
│   └── components/
│       ├── Quadrant.js         # Video quadrant component
│       ├── CaptionCard.js      # Caption text card component
│       ├── ExportBar.js        # Export buttons component
│       ├── ProcessingModal.js  # AI processing animation
│       └── UploadZone.js       # Drag-and-drop upload zone
├── config.yaml                 # Application configuration
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## 🎨 Design

The UI features a **dark glassmorphism** aesthetic with:
- Animated gradient mesh background
- Floating particle effects
- Glass panels with backdrop blur
- Smooth micro-animations on all interactions
- Responsive layout (4-col → 2-col → 1-col)

### Caption Style Colors
| Style | Color | Hex |
|-------|-------|-----|
| Formal | 🔵 Blue | `#60a5fa` |
| Sarcastic | 🩷 Pink | `#f472b6` |
| Humorous-Tech | 🟣 Purple | `#a78bfa` |
| Humorous-NonTech | 🟢 Emerald | `#34d399` |

## 🔧 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/upload` | Upload a video file |
| POST | `/api/process/{video_id}` | Start processing pipeline |
| GET | `/api/status/{video_id}` | Get processing status |
| GET | `/api/video/{video_id}/{style}` | Stream styled video |
| GET | `/api/captions/{video_id}` | Get all captions |
| GET | `/api/export/json/{video_id}` | Export captions as JSON |
| GET | `/api/export/srt/{video_id}/{style}` | Export SRT subtitle |
| POST | `/api/export/full-zip/{video_id}` | Export master ZIP |

## 🔑 API Key

CapturaAI uses [Fireworks AI](https://fireworks.ai/) for caption generation.

1. Get your API key from [fireworks.ai/account/api-keys](https://fireworks.ai/account/api-keys)
2. Enter it in the app header (stored locally in your browser)
3. Keys must start with `fw_` and be 32+ characters

## 📝 License

Built for the Antigravity IDE + Fireworks AI Hackathon.

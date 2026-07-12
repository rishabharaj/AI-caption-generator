# 🎬 Vdcap.AI — 4-Style Video Captioning Platform

<p align="center">
  <img src="frontend/favicon.svg" width="100" height="100" alt="Vdcap.AI Logo" />
</p>

<p align="center">
  <strong>Generate 4 distinct caption styles for any video and compare them side-by-side</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/FastAPI-0.100.0+-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Fireworks_AI-API-FF6F00?style=for-the-badge&logo=ai&logoColor=white" alt="Fireworks AI" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License" />
</p>

---

## 🎥 Demo

Watch the demo video of Vdcap.AI in action:
👉 **[Watch Demo Video on Google Drive](https://drive.google.com/file/d/1m-pJfh01nytF624imxM-3VgfMqjtAVpT/view?usp=drivesdk)**

---

## ✨ Features

- **4-Quadrant Split View** — Watch the same video with 4 different caption styles burned in, playing in perfect sync.
- **4 Caption Styles** — Formal, Sarcastic, Humorous-Tech, and Humorous-NonTech.
- **Audio + Visual Analysis** — Uses Whisper for transcription + frame analysis for context.
- **No Audio? No Problem** — Falls back to visual-only analysis for mute videos.
- **Stunning Dark UI** — Glassmorphism design with smooth animations, vertical timelines, and micro-interactions.
- **Export Everything** — JSON, SRT, individual/bundled MP4s, HTML reports, master ZIP.
- **Mock AI Fallback** — Works without an API key using intelligent template-based generation.
- **Fine-tuning Ready** — Pipeline for training on MSR-VTT and ActivityNet datasets.

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **ffmpeg** installed and available in PATH:
  - **Windows**: `winget install ffmpeg` or download from [ffmpeg.org](https://ffmpeg.org/download.html)
  - **macOS**: `brew install ffmpeg`
  - **Linux**: `sudo apt install ffmpeg`

### Installation

```bash
# Clone the repository
git clone https://github.com/rishabharaj/AI-caption-generator.git
cd AI-caption-generator

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
# Start the backend server
python -m backend.main
```

The app will be available at **http://localhost:8000**

---

## 📂 Project Structure

```
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
│   ├── favicon.svg             # Subtitle-themed tab icon
│   ├── images/
│   │   ├── pipeline_hero.jpg   # 5-step pipeline infographic
│   │   ├── step1.jpg           # Step 1 background asset
│   │   ├── step2.jpg           # Step 2 background asset
│   │   ├── step3.jpg           # Step 3 background asset
│   │   ├── step4.jpg           # Step 4 background asset
│   │   └── step5.jpg           # Step 5 background asset
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

---

## 🎨 Design System

The UI features a **dark glassmorphism** aesthetic with:
- Animated gradient mesh background.
- Floating particle effects.
- Glass panels with backdrop blur.
- Smooth micro-animations on all interactions.
- Responsive layout (4-col → 2-col → 1-col).

### Caption Style Colors
| Style | Color | Hex |
|-------|-------|-----|
| Formal | 🔵 Blue | `#60a5fa` |
| Sarcastic | 🩷 Pink | `#f472b6` |
| Humorous-Tech | 🟣 Purple | `#a78bfa` |
| Humorous-NonTech | 🟢 Emerald | `#34d399` |

---

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

---

## 🔑 API Key

Vdcap.AI uses [Fireworks AI](https://fireworks.ai/) for caption generation.

1. Get your API key from [fireworks.ai/account/api-keys](https://fireworks.ai/account/api-keys)
2. Enter it in the app header (stored locally in your browser)
3. Keys must start with `fw_` and be 32+ characters

---

## 📝 License

Distributed under the MIT License. See `LICENSE` for more information.

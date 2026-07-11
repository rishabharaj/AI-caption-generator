# CapturaAI — 4-Style Video Captioning Platform

## Complete Specification Document

---

## 🚀 CORE CONCEPT

CapturaAI is a premium Python web application for a Video Captioning hackathon. It generates **4 distinct caption styles** for short video clips (30 seconds to 2 minutes) and renders them in a unique **"4-Quadrant Split View"** with a stunning dark glassmorphism UI.

The user uploads a video. The app processes it and displays:

- **TOP SECTION**: 4 video quadrants playing simultaneously — the SAME video but with 4 different caption styles burned into each one
- **BOTTOM SECTION**: 4 text cards showing the raw captions for each style
- **EXPORT BAR**: Download options for JSON, SRT, individual MP4s, and a ZIP bundle

This allows instant visual + textual comparison of all 4 styles. The unique selling point is the side-by-side synchronized playback with burned captions.

---

## 🎨 VISUAL DESIGN SYSTEM — GLASSMORPHISM DARK MODE

### Color Palette

```css
:root {
  --bg-base: #0a0a0f;
  --bg-gradient-start: #1a1a2e;
  --bg-gradient-end: #000000;
  --glass-bg: rgba(255, 255, 255, 0.04);
  --glass-bg-hover: rgba(255, 255, 255, 0.07);
  --glass-border: rgba(255, 255, 255, 0.08);
  --glass-border-hover: rgba(255, 255, 255, 0.15);
  --glass-blur: blur(24px) saturate(180%);
  --text-primary: #e8e8f0;
  --text-secondary: #8b8b9e;
  --text-accent: #a78bfa;
  --accent-indigo: #6366f1;
  --accent-glow: 0 0 20px rgba(99, 102, 241, 0.3);
  --success: #10b981;
  --warning: #f59e0b;
  --error: #ef4444;
  --shadow-card: 0 4px 24px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.05);
  --shadow-card-hover: 0 8px 32px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(99, 102, 241, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.1);
}
```

### Background

- Base: `radial-gradient(ellipse at top, var(--bg-gradient-start) 0%, var(--bg-base) 50%, var(--bg-gradient-end) 100%)`
- Animated gradient mesh: 3 large soft blobs (purple `#4c1d95`, blue `#1e3a8a`, indigo `#312e81`) moving slowly in 20s CSS animation cycle
- Floating particles: 50 tiny dots (1-2px), opacity 0.08, drifting with CSS animation
- NO background images — pure CSS only

### Glassmorphism Card Spec (Apply to ALL panels/cards)

```css
.glass-panel {
  background: var(--glass-bg);
  backdrop-filter: blur(24px) saturate(180%);
  -webkit-backdrop-filter: blur(24px) saturate(180%);
  border: 1px solid var(--glass-border);
  border-radius: 16px;
  box-shadow: var(--shadow-card);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.glass-panel:hover {
  background: var(--glass-bg-hover);
  border-color: var(--glass-border-hover);
  box-shadow: var(--shadow-card-hover);
  transform: translateY(-2px);
}
```

### Typography

- Headings: `Inter`, weight 700, letter-spacing -0.02em
- Body: `Inter`, weight 400, line-height 1.6
- Labels: `Inter`, weight 500, 0.875rem, uppercase, letter-spacing 0.05em
- Monospace: `JetBrains Mono`, weight 400 (for timestamps, API logs)

### Style Badge Colors (for the 4 quadrants)

- **Formal**: `#60a5fa` (blue) with glow `box-shadow: 0 0 12px rgba(96, 165, 250, 0.4)`
- **Sarcastic**: `#f472b6` (pink) with glow `box-shadow: 0 0 12px rgba(244, 114, 182, 0.4)`
- **Humorous-Tech**: `#a78bfa` (purple) with glow `box-shadow: 0 0 12px rgba(167, 139, 250, 0.4)`
- **Humorous-NonTech**: `#34d399` (emerald) with glow `box-shadow: 0 0 12px rgba(52, 211, 153, 0.4)`

---

## 📐 UI LAYOUT

### Header (64px, sticky, glass)

```
[Logo: "CapturaAI"]  [Upload Video Button]  [Fireworks API Key Input]  [Settings]
```

### Main Content Area

```
┌─────────────────────────────────────────────────────────────────────┐
│  HEADER (glass, sticky, z-index: 100)                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ │
│  │ 🔵 FORMAL    │ │ 🟣 SARCASTIC │ │ 🟣 HUMOR-TECH│ │ 🟢 HUMOR-NON │ │
│  │              │ │              │ │              │ │              │ │
│  │   [VIDEO]    │ │   [VIDEO]    │ │   [VIDEO]    │ │   [VIDEO]    │ │
│  │   + Caption  │ │   + Caption  │ │   + Caption  │ │   + Caption  │ │
│  │              │ │              │ │              │ │              │ │
│  │  ⬇ Download  │ │  ⬇ Download  │ │  ⬇ Download  │ │  ⬇ Download  │ │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘ │
│                                                                     │
│  [◀◀ -10s]  [▶ Play All]  [⏸ Pause All]  [▶▶ +10s]  [🔁 Replay]    │
│  ═══════════════════════════════════════════════════════════ Seek Bar │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│  CAPTION CARDS                                                      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ │
│  │ FORMAL TEXT  │ │ SARCASTIC    │ │ HUMOR-TECH   │ │ HUMOR-NON    │ │
│  │              │ │ TEXT         │ │ TEXT         │ │ TEXT         │ │
│  │ [Copy][Edit] │ │ [Copy][Edit] │ │ [Copy][Edit] │ │ [Copy][Edit] │ │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘ │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│  EXPORT BAR (glass pill, centered)                                  │
│  [📄 JSON]  [📝 SRT]  [🎬 All 4 Videos]  [📊 Report]  [📥 ZIP All]   │
└─────────────────────────────────────────────────────────────────────┘
```

### Quadrant Video Cards

Each is a glass card with:
- Top-left badge: style name with colored background (see badge colors above)
- Top-right: download icon button (glass circle, 32px)
- Video fills the card, rounded corners (12px)
- Caption text burned into the video preview (white text, black stroke, centered bottom)
- Bottom: small timestamp indicator
- Hover: scale(1.02), border glow intensifies, download button appears if hidden

### Caption Text Cards (Below Videos)

- Same glassmorphism style
- 4px colored left border matching quadrant badge color
- Text is selectable and content-editable
- Bottom-right: character count badge
- Action buttons: Copy (📋), Edit (✏️), Regenerate (🔄)
- Copy button: icon changes to ✅ for 1.5s then reverts
- Hover: card lifts slightly, border glow

### Sync Playback Controls

- Glass pill-shaped container, centered between video grid and caption cards
- Buttons: glassmorphism with hover glow (indigo)
- Seek bar: thin line (rgba(255,255,255,0.1)), active portion (indigo), thumb (glowing circle)
- All 4 videos play/pause/seek in PERFECT sync

### Export Bar

- Glass pill, sticky bottom, padding 16px 32px
- Buttons: glassmorphism with subtle colored left border
- Primary action (ZIP All): indigo background with glow
- On hover: buttons lift, glow intensifies

---

## ⚡ LOADING & PROCESSING ANIMATIONS

### 1. Upload Phase

- **Drag Zone**: Dashed border (2px dashed rgba(255,255,255,0.2)), dashed animation (border moves)
- **On Drag Over**: Border glows indigo, background shifts to rgba(99,102,241,0.05), scale(1.02)
- **On Drop**: Ripple effect from center (CSS radial animation), then card flips to processing state

### 2. AI Processing State (The "Wow" Factor)

- **Central Glass Card** with animated neural network SVG:
  - 6 nodes in a hexagon pattern, pulsing in sequence (indigo → purple → pink)
  - Connection lines draw themselves with stroke-dashoffset animation (2s cycle)
  - Subtle radial glow behind: `radial-gradient(circle, rgba(99,102,241,0.2) 0%, transparent 70%)`
- **Progress Steps** (vertical timeline inside the card):
  1. "Extracting video frames..." → 3 orbiting dots animation
  2. "Analyzing audio stream..." → animated waveform bars (5 bars, random heights, smooth)
  3. "Transcribing speech..." → typing cursor effect on sample text
  4. "Generating captions (4 styles)..." → 4 small dots that fill one by one with style colors
  5. "Burning subtitles into videos..." → horizontal progress bar with shimmer effect
  6. "Ready! 🎉" → emerald checkmark with subtle scale-in + 20 confetti particles (CSS)
- **Status Indicators** per step:
  - Pending: dim gray dot (rgba(255,255,255,0.2))
  - Processing: pulsing indigo dot with ring ripple animation
  - Complete: emerald checkmark with scale-in (0.8 → 1.0)

### 3. Skeleton Loading (While captions generate)

- 4 glass cards with shimmer skeleton lines:
  - Shimmer: `linear-gradient(90deg, transparent, rgba(255,255,255,0.06), transparent)` animation
  - 3 lines per card, staggered widths (100%, 80%, 60%)
- Staggered reveal: cards appear one by one with 0.15s delay, fade-up (translateY(20px) → 0) + opacity

### 4. Video Playback Loading

- Before video plays: dual-ring spinner in center of each quadrant
  - Outer ring: 40px, indigo, rotates clockwise (1s linear infinite)
  - Inner ring: 24px, purple, rotates counter-clockwise (0.8s linear infinite)
- On ready: spinner fades out, video fades in (0.3s)

### 5. Download Animation

- On click: button icon morphs to spinner (same color)
- On complete: morphs to green checkmark with scale bounce
- Reverts to original icon after 2s

---

## 🎬 VIDEO PROCESSING PIPELINE

### 1. Input Handling

- Accept MP4, MOV, AVI, WEBM (30 seconds to 2 minutes)
- File size limit: 500MB
- Validate duration on upload (reject if <30s or >2min)

### 2. Audio Detection

Use ffmpeg to detect audio streams:

```bash
ffmpeg -i input.mp4 -show_streams -select_streams a -loglevel error
```

**WITH AUDIO**:
- Extract audio to WAV (16kHz, mono) using ffmpeg
- Transcribe using OpenAI Whisper (local or API)
- Use transcript + key visual frames for caption context

**WITHOUT AUDIO**:
- Extract frames at 1 FPS using ffmpeg/OpenCV
- Generate visual descriptions (scene understanding, objects, actions, mood)
- Use ONLY visual context for caption generation
- Show a "🔇 No Audio Detected — Visual Analysis Only" badge in UI

### 3. Frame Extraction

Extract 1 FPS using ffmpeg:

```bash
ffmpeg -i input.mp4 -vf "fps=1,scale=480:-1" frames/%04d.jpg
```

Select 5-10 representative frames evenly distributed across the video. Use these frames as visual context for the AI model.

### 4. Caption Generation (Fireworks AI)

- **API Endpoint**: `https://api.fireworks.ai/inference/v1/chat/completions`
- **Model**: `accounts/fireworks/models/llama-v3p1-8b-instruct`
- **API Key**: Stored in browser localStorage (key: `fireworks_api_key`), sent from client
- **Fallback**: If no API key, use a Local Mock AI that generates plausible captions based on video metadata

### 5. Four Caption Styles (System Prompts)

**FORMAL:**
```
You are a professional documentary narrator. Describe the video in a formal, objective, and eloquent manner. Use proper grammar, sophisticated vocabulary, and a neutral tone. Focus on the key events, actions, and visual elements. Keep it concise (2-3 sentences).
```

**SARCASTIC:**
```
You are a witty, sarcastic commentator. Write a dry, ironic caption about this video. Use understated humor, subtle mockery, and a deadpan tone. Make it clever but not mean-spirited. 1-2 sentences max.
```

**HUMOROUS-TECH:**
```
You are a tech-savvy comedian. Write a funny caption with references to startups, programming, AI, Silicon Valley culture, or geek life. Use tech jargon humorously. Make it relatable to developers and tech enthusiasts. 1-2 sentences.
```

**HUMOROUS-NON-TECH:**
```
You are a general audience comedian. Write a funny, accessible caption that anyone can understand. No tech jargon. Use observational humor, pop culture references, or witty wordplay. Keep it light and universally funny. 1-2 sentences.
```

### 6. Caption Burning (ffmpeg)

Generate 4 separate MP4 files using ffmpeg drawtext filter:

```bash
ffmpeg -i input.mp4 -vf "drawtext=fontfile=Inter-Bold.ttf:text='CAPTION':fontcolor=white:fontsize=24:borderw=2:bordercolor=black:x=(w-text_w)/2:y=h-text_h-40:line_spacing=4" -c:a copy output.mp4
```

Text specs:
- Font: Inter Bold, 24px
- Color: white (#ffffff)
- Stroke: black, 2px
- Background bar: rgba(0,0,0,0.5) behind text for readability
- Position: centered, bottom, 10% padding from bottom
- Line wrapping: max width 90% of video width
- All outputs maintain original resolution and frame rate

---

## 🔧 FIREWORKS AI INTEGRATION

### API Client

```python
# fireworks_client.py
import requests
from typing import List, Dict

class FireworksClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.fireworks.ai/inference/v1"

    def generate_caption(self, style: str, transcript: str, visual_context: List[str]) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        system_prompts = {
            "formal": "You are a professional documentary narrator...",
            "sarcastic": "You are a witty, sarcastic commentator...",
            "humorous_tech": "You are a tech-savvy comedian...",
            "humorous_non_tech": "You are a general audience comedian..."
        }

        payload = {
            "model": "accounts/fireworks/models/llama-v3p1-8b-instruct",
            "messages": [
                {"role": "system", "content": system_prompts[style]},
                {"role": "user", "content": f"Video transcript: {transcript}\nVisual context: {visual_context}"}
            ],
            "max_tokens": 150,
            "temperature": 0.8
        }

        response = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
        return response.json()["choices"][0]["message"]["content"]
```

### Fallback Mock AI

If no API key, analyze transcript keywords and generate template-based captions. Maintain the 4 distinct tones using rule-based generation.

---

## 🎓 FINE-TUNING PIPELINE

### Script: `train_captioner.py`

Support fine-tuning on open video-caption datasets:
- MSR-VTT
- ActivityNet Captions
- WebVid (if available)

Two training modes:
1. **Audio+Visual**: Uses transcript + visual frames
2. **Visual-Only**: Uses only visual frames (for mute videos)

### Implementation

Use Fireworks AI fine-tuning API if available, OR local fine-tuning with Hugging Face Transformers + PEFT (LoRA).

Config toggle in `config.yaml`:

```yaml
model:
  use_fine_tuned: false
  fine_tuned_model_id: ""
  base_model: "accounts/fireworks/models/llama-v3p1-8b-instruct"
```

### Training Data Format

```json
{
  "video_id": "vid_001",
  "transcript": "person speaking...",
  "visual_frames": ["frame1.jpg", "frame2.jpg"],
  "captions": {
    "formal": "...",
    "sarcastic": "...",
    "humorous_tech": "...",
    "humorous_non_tech": "..."
  }
}
```

---

## 📥 DOWNLOAD & EXPORT SYSTEM

### 1. Individual Video Downloads

- Each quadrant has a download button (top-right, glass circle icon)
- **Flow**: Click → spinner (1s) → download starts → checkmark (2s) → revert
- **Endpoint**: `GET /api/download/{video_id}/{style}`
- **Filename**: `{original_name}_{style}.mp4` (e.g., `clip_formal.mp4`)

### 2. JSON Export

- **Endpoint**: `GET /api/export/json/{video_id}`
- **Filename**: `{video_id}_captions.json`
- **Format**:

```json
{
  "project": "CapturaAI Export",
  "exported_at": "2026-07-11T08:45:00Z",
  "video": {
    "filename": "clip.mp4",
    "duration": 45.5,
    "has_audio": true,
    "resolution": "1920x1080",
    "fps": 30
  },
  "captions": {
    "formal": {
      "text": "A person demonstrates...",
      "style": "formal",
      "word_count": 24,
      "confidence": 0.94
    },
    "sarcastic": {
      "text": "Oh great, another person...",
      "style": "sarcastic",
      "word_count": 18,
      "confidence": 0.91
    },
    "humorous_tech": {
      "text": "When your neural net...",
      "style": "humorous_tech",
      "word_count": 15,
      "confidence": 0.89
    },
    "humorous_non_tech": {
      "text": "This guy really said...",
      "style": "humorous_non_tech",
      "word_count": 12,
      "confidence": 0.92
    }
  }
}
```

### 3. SRT Export (Per Style + Combined)

- **Individual**: `GET /api/export/srt/{video_id}/{style}`
- **Combined**: `GET /api/export/srt-combined/{video_id}`
- **Combined SRT Format**:

```
1
00:00:00,000 --> 00:00:05,000
[FORMAL] A person demonstrates...

2
00:00:00,000 --> 00:00:05,000
[SARCASTIC] Oh great, another person...

3
00:00:00,000 --> 00:00:05,000
[HUMOR-TECH] When your neural net...

4
00:00:00,000 --> 00:00:05,000
[HUMOR-NONTECH] This guy really said...
```

### 4. All 4 Videos Bundle

- **Endpoint**: `POST /api/export/videos-zip/{video_id}`
- Returns ZIP containing all 4 styled MP4s
- **Filename**: `{video_id}_all_styles.zip`

### 5. Full Report (HTML)

- **Endpoint**: `GET /api/export/report/{video_id}`
- Generates a printable HTML page:
  - Header with project name and timestamp
  - Video metadata table
  - 4 video thumbnails (base64) in a grid
  - All 4 captions in styled cards
  - "Print to PDF" button
  - Clean, minimal design matching the app aesthetic

### 6. Master ZIP (Everything)

- **Endpoint**: `POST /api/export/full-zip/{video_id}`
- **Modal**: Glass card with checkboxes:
  - ☑ All 4 Styled Videos
  - ☑ JSON captions
  - ☑ SRT files (individual + combined)
  - ☑ HTML Report
  - ☑ Original transcript
- **Progress**: Circular SVG progress bar (indigo stroke) while zipping
- **Filename**: `CapturaAI_Export_{video_id}_{timestamp}.zip`

---

## 🎮 SYNC PLAYBACK SYSTEM

### Features

- All 4 videos play/pause/seek in PERFECT synchronization
- **Play All**: Starts all 4 videos simultaneously
- **Pause All**: Pauses all 4 simultaneously
- **Seek Bar**: Dragging seeks all 4 videos to the same timestamp
- **+10s / -10s**: Jumps all videos forward/backward
- **Replay**: Resets all to 0:00 and plays
- **Mute Toggle**: Individual mute per quadrant + global mute

### Implementation

Use HTML5 Video API with `currentTime` synchronization. Event listeners: `play`, `pause`, `timeupdate`, `seeking`, `seeked`. Sync drift correction: every 100ms, check if any video is >0.2s out of sync and correct.

---

## 📂 PROJECT STRUCTURE

```
video-captioner/
├── backend/
│   ├── main.py                 # FastAPI application entry
│   ├── config.py               # Config loader (YAML)
│   ├── api/
│   │   ├── routes.py           # All FastAPI endpoints
│   │   ├── dependencies.py     # API key validation, auth
│   │   └── exceptions.py       # Custom error handlers
│   ├── services/
│   │   ├── video_processor.py  # ffmpeg frame + audio extraction
│   │   ├── audio_detector.py   # Detect if video has audio
│   │   ├── whisper_client.py   # OpenAI Whisper integration
│   │   ├── caption_generator.py # 4-style prompt engine
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
│   ├── index.html               # Main dashboard
│   ├── style.css                # Glassmorphism design system
│   ├── main.js                  # Sync playback, API calls
│   ├── animations.js            # Loading effects, particles, shimmer
│   ├── components/
│   │   ├── Quadrant.js          # Video quadrant component
│   │   ├── CaptionCard.js       # Caption text card component
│   │   ├── ExportBar.js         # Export buttons component
│   │   ├── ProcessingModal.js   # AI processing animation modal
│   │   └── UploadZone.js        # Drag-and-drop upload zone
│   └── assets/
│       ├── fonts/               # Inter, JetBrains Mono
│       └── icons/               # SVG icons
├── config.yaml
├── requirements.txt
└── README.md
```

---

## 🎯 KEY INTERACTIONS & MICRO-ANIMATIONS

1. **Page Load**: Staggered fade-in of all glass panels (0.1s delay each, translateY(20px) → 0)
2. **Upload**: File drop triggers ripple + card flip to processing state
3. **Processing**: Neural network SVG animation + step timeline with colored indicators
4. **Completion**: 4 quadrants slide in from bottom with stagger, videos auto-play muted
5. **Hover on Quadrant**: Border glow + slight scale + style badge pulses
6. **Copy Caption**: Button morphs to checkmark with green flash (1.5s)
7. **Edit Caption**: Pencil icon toggles contentEditable, border turns amber
8. **Export**: Circular progress SVG + checkmark on completion
9. **Error State**: Glass card shakes (CSS keyframe), red glow border, toast notification slides in from top-right
10. **Scroll**: Header becomes more opaque (glass blur increases) on scroll

---

## 🔐 API KEY MANAGEMENT

- Input field in header: "Enter Fireworks API Key (fw_...)"
- Stored in browser localStorage: `localStorage.setItem('fireworks_api_key', key)`
- Sent with every API request in Authorization header
- Validation: Check key starts with "fw_" and is 32+ characters
- Show "🔒 Secure — stored locally" badge next to input
- If no key: show warning toast + enable Mock AI fallback automatically

---

## 📝 NOTES FOR DEVELOPER

- The 4-quadrant split view is the KEY differentiator — make it polished and demo-ready
- Glassmorphism must be consistent across ALL components
- Animations should feel smooth, not janky — use `transform` and `opacity` only for 60fps
- Video sync is critical — test with videos of different lengths and formats
- Handle edge cases: no audio, corrupted video, API failure, network timeout
- Mobile responsive: on screens <1024px, stack quadrants 2x2; on <640px, single column
- Performance: lazy load videos, compress frames before sending to AI, cache captions
- Accessibility: proper ARIA labels, keyboard navigation, reduced-motion support

---

*Generated for Antigravity IDE + Fireworks AI Hackathon*

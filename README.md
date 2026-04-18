<div align="center">

<img src="https://img.shields.io/badge/AttentionX-MVP%201.0-7F77DD?style=for-the-badge&logo=lightning&logoColor=white" alt="AttentionX"/>

# ⚡ AttentionX

### AI-Powered Automated Content Repurposing Engine

**Turn a 60-minute workshop into a week of viral content — automatically.**

[![Demo Video](https://img.shields.io/badge/▶%20Watch%20Demo-Google%20Drive-4285F4?style=for-the-badge&logo=googledrive&logoColor=white)](https://drive.google.com/your-link-here)
[![Live App](https://img.shields.io/badge/🚀%20Live%20App-Deployed-22c55e?style=for-the-badge)](https://attention-x-ai.vercel.app)
[![GitHub](https://img.shields.io/badge/GitHub-Public%20Repo-181717?style=for-the-badge&logo=github)](https://github.com/Piyusha942007/AttentionX-AI)

</div>

---

## 🎯 The Problem We Solve

Mentors, educators, and creators produce hours of high-value long-form video. But modern audiences consume content in **60-second bursts**. The most profound insights — a framework that could change someone's career, a story that reframes everything — are buried inside 60-minute recordings that most people never finish watching.

**The Wisdom Gap:** Valuable knowledge exists. Audiences exist. The bridge doesn't.

AttentionX closes that gap. Upload one session → get a week's worth of viral, vertical, caption-ready clips.

---

## 🎬 Demo

> **[▶ Watch the full demo on Google Drive](https://drive.google.com/your-link-here)**

The demo walks through:
1. Uploading a 60-minute mentorship session
2. Live emotional peak detection on the waveform timeline
3. Auto-generated virality scores and hook headlines
4. Smart 9:16 crop with face tracking
5. Karaoke-style caption export

---

## ✨ Key Features

| Feature | What it does |
|---|---|
| **Emotional Peak Detection** | Fuses Librosa audio energy + Gemini sentiment scoring to find the most impactful 60-second windows |
| **Virality Score** | Each detected clip gets a 0–100% score based on audio intensity, sentiment profundity, and content type |
| **Smart Vertical Crop** | MediaPipe face tracking keeps the speaker centered in a 9:16 frame — no manual cropping |
| **Karaoke Captions** | Word-level Whisper timestamps drive animated, high-contrast caption overlays |
| **Hook Headline Generator** | Gemini generates a scroll-stopping 5–8 word headline for each clip automatically |
| **One-Click Export** | Burned-in captions + title card + 9:16 vertical MP4 ready for TikTok, Reels, and Shorts |

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    React Frontend (Vite)                  │
│         Upload Zone → Peak Timeline → Clip Preview        │
└────────────────────────┬─────────────────────────────────┘
                         │ REST API
┌────────────────────────▼─────────────────────────────────┐
│                  FastAPI Backend (Python)                  │
│            Job Queue → Status Updates → Storage           │
└──────┬──────────────────────────────────────┬────────────┘
       │                                      │
┌──────▼───────────┐              ┌───────────▼────────────┐
│  AI Analysis     │              │  Video Processing       │
│  Pipeline        │              │  Engine                 │
│                  │              │                         │
│  • OpenAI Whisper│              │  • MediaPipe face track │
│  • Librosa RMS   │              │  • MoviePy crop/clip    │
│  • Gemini Flash  │              │  • Caption burn-in      │
│  • Virality Fuse │              │  • 9:16 export          │
└──────────────────┘              └─────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────┐
│              Supabase (Storage + Postgres)                 │
│         Job tracking · Clip storage · User data           │
└──────────────────────────────────────────────────────────┘
```

---

## 🧠 How the Viral Signal Algorithm Works

AttentionX doesn't guess — it fuses **three independent AI signals** to find the golden nuggets:

**Signal A — Audio Energy (Librosa)**
Extracts RMS energy per frame, normalizes, and smooths with a rolling average. Detects where the speaker is most passionate and energized.

**Signal B — Sentiment & Profundity (Gemini 1.5 Flash)**
Sends the full transcript (Gemini's 1M token context window handles 60+ minute sessions in one call) and scores each segment for: personal vulnerability, counterintuitive claims, actionable frameworks, and quotable one-liners.

**Signal C — Timestamps (Whisper)**
Word-level timestamps from OpenAI Whisper power karaoke-style captions — each word highlights exactly as it's spoken.

**Fusion:**
```
virality_score = (0.4 × audio_energy) + (0.6 × gemini_score)
```
Top 5 non-overlapping windows (min 90s gap) become your clips.

---

## 🎥 Smart Crop Logic

```
16:9 source (1920×1080)  →  9:16 output (608×1080)
```

1. MediaPipe detects the speaker's face center X coordinate per frame (every 3rd frame for speed)
2. A 30-frame rolling average smooths the crop window to eliminate jitter
3. The crop window is clamped to frame bounds so it never goes out of range
4. MoviePy applies the per-frame crop function at export time

The result: the speaker stays centered in frame throughout the entire clip, even if they move.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- ffmpeg installed (`brew install ffmpeg` or `apt install ffmpeg`)
- API keys: Google Gemini, OpenAI, Supabase

### Installation

```bash
# Clone the repository
git clone https://github.com/Piyusha942007/AttentionX-AI.git
cd attentionx

# Backend setup
cd backend
pip install -r requirements.txt
cp .env.example .env
# Fill in your API keys in .env

# Frontend setup
cd ../frontend
npm install
cp .env.example .env.local
# Fill in your Supabase URL and anon key
```

### Environment Variables

**Backend `.env`:**
```env
GEMINI_API_KEY=your_gemini_api_key
OPENAI_API_KEY=your_openai_api_key
SUPABASE_URL=your_supabase_project_url
SUPABASE_SERVICE_KEY=your_supabase_service_key
```

**Frontend `.env.local`:**
```env
VITE_SUPABASE_URL=your_supabase_project_url
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
VITE_API_URL=http://localhost:8000
```

### Running Locally

```bash
# Terminal 1 — Backend
cd backend
uvicorn main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend
npm run dev
```

Open [http://localhost:5173](http://localhost:5173)

---

## 📁 Project Structure

```
attentionx/
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   └── Dashboard.jsx          # Main 3-panel layout
│   │   ├── components/
│   │   │   ├── UploadZone.jsx         # Drag-and-drop file input
│   │   │   ├── PeakTimeline.jsx       # Waveform + peak markers
│   │   │   ├── NuggetCard.jsx         # Individual clip card
│   │   │   └── PreviewPane.jsx        # Side-by-side 16:9 / 9:16
│   │   └── App.jsx
│   └── package.json
│
├── backend/
│   ├── main.py                        # FastAPI app + routes
│   ├── models.py                      # Pydantic schemas
│   ├── db.py                          # Supabase client
│   ├── worker.py                      # Background job processor
│   └── services/
│       ├── transcriber.py             # OpenAI Whisper wrapper
│       ├── analyzer.py                # Gemini sentiment analysis
│       ├── scorer.py                  # Librosa + fusion scoring
│       ├── face_tracker.py            # MediaPipe face detection
│       ├── cropper.py                 # MoviePy vertical crop
│       └── captioner.py              # Karaoke caption burn-in
│
└── README.md
```

---

## 🛠️ Tech Stack

**Frontend**
- React 18 + Vite
- Tailwind CSS
- Recharts (waveform visualization)

**Backend**
- FastAPI (Python)
- asyncio background workers

**AI / ML**
- Google Gemini 1.5 Flash — sentiment analysis & hook generation
- OpenAI Whisper — transcription with word-level timestamps
- Librosa — audio energy / RMS extraction
- MediaPipe — real-time face detection & tracking

**Video Processing**
- MoviePy — clip cutting, cropping, export
- ffmpeg — encoding and caption burn-in

**Infrastructure**
- Supabase — Postgres job tracking + object storage
- Vercel — frontend hosting
- Railway / Render — backend hosting

---

## 📊 Evaluation Criteria Mapping

| Criterion | How AttentionX delivers |
|---|---|
| **Impact (20%)** | Turns 1 hour of content into 5 ready-to-publish clips in under 5 minutes |
| **Innovation (20%)** | 3-signal virality fusion (audio + semantic AI + timing) is novel; no existing tool does this |
| **Technical Execution (20%)** | Clean modular Python services, typed FastAPI endpoints, React component architecture |
| **User Experience (25%)** | Premium dark dashboard, real-time waveform, one-click export, demo mode for instant wow |
| **Presentation (15%)** | Full demo video linked above showing end-to-end flow on a real 60-min session |

---

## 🎥 Recording Your Demo

The demo video is hosted on Google Drive:

**[▶ Watch Demo — Google Drive](https://drive.google.com/your-link-here)**

*Replace the link above with your actual Google Drive share link before submission.*

---

## 👥 Team

Built for the **AttentionX AI Hackathon** by **UnsaidTalks Education**

| Role | Responsibility |
|---|---|
| Full Stack | React dashboard, FastAPI backend, Supabase integration |
| AI/ML | Gemini pipeline, Whisper transcription, virality scoring |
| Media Engineering | MediaPipe tracking, MoviePy crop, caption burn-in |

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

Built with ⚡ for the AttentionX AI Hackathon · UnsaidTalks Education · 2026

</div>
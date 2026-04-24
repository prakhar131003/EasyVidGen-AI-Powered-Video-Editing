# 🎬 EasyVidGen

EasyVidGen is a PySide6 applicaion that automatically uses AI to creates videos from audio files. It transcribes speech using OpenAI Whisper, splits audio into intelligent 3–10 second chunks aligned with sentence boundaries, generates key phrases to use as search query using an LLM served via Ollama, fetches stock media from Pexels, and assembles everything with smooth crossfade transitions. Users can edit chunks, replace media, and preview results – all through an intuitive project-based GUI. Perfect for automating and/or streamlining video editing workflows.

## ✨ Features

- **Project-based workflow** – Create, save, and load projects with persistent media storage.
- **Audio transcription** – Whisper (base model) with word‑level timestamps.
- **Intelligent chunking** – Split audio into 3–10 second chunks aligned with sentence boundaries (no mid‑sentence cuts).
- **Key Phrase generation** – Uses Ollama (local LLM) to produce search queries for each chunk; falls back to local extraction if server unavailable.
- **Stock video fetching** – 1080p videos from Pexels API (free tier).
- **Full editing capability** – Edit chunk text, regenerate keywords, replace media with local files, and preview any chunk.
- **Smooth video assembly** – Crossfade transitions (video + audio) with MoviePy; final video saved in project folder.
- **Segment management** – Add multiple audio segments, delete unwanted segments with associated files.

## 🖥️ GUI Preview

The application is built with **PySide6** which is a Python implementation of Qt6, it allows:

* Project creation/loading interface
* Segment list with add/edit/delete buttons
* Progress log with timestamps
* Chunk editing table with media preview

## 📦 Installation

### Prerequisites

* Python 3.10 or higher
* [FFmpeg](https://ffmpeg.org/download.html) – must be in system PATH (required by MoviePy)
* [Ollama](https://ollama.com/download) – running locally with a model (e.g., `gemma4:e4b`)
* [Pexels API key](https://www.pexels.com/api/) – free tier

### Clone \& Setup

```
git clone https://github.com/yourusername/youtube-video-generator.git
cd youtube-video-generator
python -m venv venv
source venv/bin/activate or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
```

### Usage Instructions

* Use ollama serve to serve an LLM of choice.
* Edit the .env file with your respective ollama serve URL and model name.
* Start with main.py.
* Upload a segment as an audio file.
* Review the segment video generation as modify as necessary.
* Once all segments have been processed, click generate to generate final full video from the processed segments.


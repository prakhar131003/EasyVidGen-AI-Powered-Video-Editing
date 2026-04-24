import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent

env_path = PROJECT_ROOT / ".env"
load_dotenv(dotenv_path=env_path)


# Pexels API
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
if not PEXELS_API_KEY:
    print("PEXELS_API_KEY not found in .env. Media fetching will fail.")
else:
    print(f"PEXELS_API_KEY loaded (starts with: {PEXELS_API_KEY[:5]}...)")

# Ollama
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

# Directory Settings
PROJECTS_DIR = "projects"
TEMP_DIR = "temp"

# Video Export Settings
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
FPS = 24
TRANSITION_DURATION = 0.5

# Audio Chunking Rules
TARGET_CHUNK_SECONDS = 6
MIN_CHUNK_SECONDS = 3
MAX_CHUNK_SECONDS = 10

DEBUG = os.getenv("DEBUG", "False").lower() == "true"

if DEBUG:
    print(f"Ollama URL: {OLLAMA_URL}")
    print(f"Ollama Model: {OLLAMA_MODEL}")
    print(f"Projects directory: {PROJECTS_DIR}")
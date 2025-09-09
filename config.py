"""Configuration settings for StudyMate application."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directories
BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
USER_DATA_DIR = BASE_DIR / "user_data"
FAISS_INDEX_DIR = BASE_DIR / "faiss_indexes"
TEMP_DIR = BASE_DIR / "temp_files"

# Create directories if they don't exist
for directory in [UPLOAD_DIR, USER_DATA_DIR, FAISS_INDEX_DIR, TEMP_DIR]:
    directory.mkdir(exist_ok=True)

# API Keys and Configuration
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "")
IBM_WATSON_API_KEY = os.getenv("IBM_WATSON_API_KEY", "")
IBM_WATSON_URL = os.getenv("IBM_WATSON_URL", "")

# Model Configuration
DEFAULT_LLM_MODEL = "gpt2"  # Use GPT-2 as it's lighter and more reliable
DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # Keep this as it's reliable
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# Supported file types
SUPPORTED_FILE_TYPES = ["pdf", "docx", "txt"]

# TTS Configuration
TTS_LANGUAGES = {
    "english": "en",
    "hindi": "hi", 
    "tamil": "ta",
    "telugu": "te",
    "bengali": "bn",
    "gujarati": "gu",
    "kannada": "kn",
    "malayalam": "ml",
    "marathi": "mr",
    "punjabi": "pa",
    "urdu": "ur"
}

# Voice options for TTS
VOICE_OPTIONS = {
    "default": "neutral",
    "academic": "formal",
    "casual": "friendly", 
    "debate_pro": "confident",
    "debate_con": "analytical"
}

# UI Configuration
APP_TITLE = "StudyMate - Your AI Learning Companion"
APP_ICON = "📚"
SIDEBAR_TITLE = "Navigation"

# Session state keys
SESSION_KEYS = {
    "user_id": "user_id",
    "documents": "uploaded_documents",
    "chat_history": "chat_history",
    "current_session": "current_session"
}
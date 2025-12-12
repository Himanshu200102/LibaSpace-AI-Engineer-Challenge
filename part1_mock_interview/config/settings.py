"""Configuration settings for the interview agent."""
import os
from dotenv import load_dotenv

load_dotenv()

# LiveKit Configuration
LIVEKIT_URL = os.getenv("LIVEKIT_URL", "")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "")

# AI Service API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY", "")

# Interview Configuration
SELF_INTRO_TIMEOUT = int(os.getenv("SELF_INTRO_TIMEOUT", "45"))  # seconds
PAST_EXPERIENCE_TIMEOUT = int(os.getenv("PAST_EXPERIENCE_TIMEOUT", "60"))  # seconds

# Model Configuration
# Note: gpt-3.5-turbo is cheaper than gpt-4/gpt-4o but still works well
# Options: gpt-3.5-turbo (cheapest), gpt-4, gpt-4-turbo, gpt-4o (most expensive)
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
TTS_VOICE = os.getenv("TTS_VOICE", "alloy")


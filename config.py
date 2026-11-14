import os
from dotenv import load_dotenv

load_dotenv()

APP_NAME = "JARVIS"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.5").strip()
VOICE_RATE = int(os.getenv("VOICE_RATE", "175"))
VOICE_VOLUME = float(os.getenv("VOICE_VOLUME", "1.0"))
LISTEN_TIMEOUT = int(os.getenv("LISTEN_TIMEOUT", "5"))
PHRASE_TIME_LIMIT = int(os.getenv("PHRASE_TIME_LIMIT", "10"))
WEATHER_DEFAULT_CITY = os.getenv("WEATHER_DEFAULT_CITY", "Bhopal").strip()

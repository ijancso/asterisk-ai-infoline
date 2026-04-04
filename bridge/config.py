import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY   = os.environ["OPENAI_API_KEY"]
WHISPER_MODEL    = os.getenv("WHISPER_MODEL", "whisper-1")
GPT_MODEL        = os.getenv("GPT_MODEL", "gpt-4o")
TTS_VOICE        = os.getenv("TTS_VOICE", "nova")

AI_PERSONA       = os.getenv(
    "AI_PERSONA",
    "You are a friendly and professional information line assistant. "
    "Answer questions clearly and concisely. Keep responses under 3 sentences."
)

MAX_CALL_DURATION = int(os.getenv("MAX_CALL_DURATION", "300"))
SILENCE_TIMEOUT   = int(os.getenv("SILENCE_TIMEOUT", "10"))
LOG_LEVEL         = os.getenv("LOG_LEVEL", "INFO")
DB_PATH           = os.getenv("DB_PATH", "/app/data/calls.db")

import io
import logging
import tempfile
from pathlib import Path

from openai import OpenAI
from pydub import AudioSegment

from config import (
    OPENAI_API_KEY,
    WHISPER_MODEL,
    GPT_MODEL,
    TTS_VOICE,
    AI_PERSONA,
)

logger = logging.getLogger(__name__)
client = OpenAI(api_key=OPENAI_API_KEY)


# ─────────────────────────────────────────────────────────────
# Speech-to-Text
# ─────────────────────────────────────────────────────────────

def transcribe_audio(audio_path: str) -> str:
    """
    Transcribe a WAV/raw audio file using Whisper.
    Returns the transcribed text, or empty string on failure.
    """
    path = Path(audio_path)
    if not path.exists() or path.stat().st_size == 0:
        logger.warning("Audio file missing or empty: %s", audio_path)
        return ""

    # Asterisk records in slin (signed linear 16-bit 8kHz).
    # Whisper accepts mp3/mp4/wav etc. — convert via pydub.
    try:
        audio = AudioSegment.from_file(audio_path, format="raw",
                                       frame_rate=8000, channels=1,
                                       sample_width=2)
        buf = io.BytesIO()
        audio.export(buf, format="mp3")
        buf.seek(0)
        buf.name = "audio.mp3"

        response = client.audio.transcriptions.create(
            model=WHISPER_MODEL,
            file=buf,
            language="en",
        )
        text = response.text.strip()
        logger.info("Whisper transcript: %r", text)
        return text

    except Exception as exc:
        logger.error("Whisper error: %s", exc)
        return ""


# ─────────────────────────────────────────────────────────────
# Chat completion
# ─────────────────────────────────────────────────────────────

def get_response(conversation: list[dict]) -> str:
    """
    Send conversation history to GPT and return the assistant's reply.
    `conversation` is a list of {"role": "user"|"assistant", "content": "..."} dicts.
    """
    messages = [{"role": "system", "content": AI_PERSONA}] + conversation

    try:
        response = client.chat.completions.create(
            model=GPT_MODEL,
            messages=messages,
            max_tokens=200,
            temperature=0.7,
        )
        reply = response.choices[0].message.content.strip()
        logger.info("GPT reply: %r", reply)
        return reply

    except Exception as exc:
        logger.error("GPT error: %s", exc)
        return "I'm sorry, I'm having trouble responding right now. Please try again in a moment."


def generate_summary(conversation: list[dict]) -> str:
    """Generate a one-line summary of the call for the database."""
    if not conversation:
        return "No conversation recorded."

    try:
        transcript_text = "\n".join(
            f"{t['role'].upper()}: {t['content']}" for t in conversation
        )
        response = client.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "Summarise this phone call transcript in one sentence.",
                },
                {"role": "user", "content": transcript_text},
            ],
            max_tokens=80,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()

    except Exception as exc:
        logger.error("Summary error: %s", exc)
        return "Summary unavailable."


# ─────────────────────────────────────────────────────────────
# Text-to-Speech
# ─────────────────────────────────────────────────────────────

def synthesise_speech(text: str, output_path: str) -> bool:
    """
    Convert text to speech using OpenAI TTS.
    Saves as 8kHz mono signed-16 PCM (slin) for Asterisk.
    Returns True on success.
    """
    try:
        response = client.audio.speech.create(
            model="tts-1",
            voice=TTS_VOICE,
            input=text,
            response_format="mp3",
        )

        mp3_data = response.content

        # Convert to slin format that Asterisk expects
        audio = AudioSegment.from_mp3(io.BytesIO(mp3_data))
        audio = audio.set_frame_rate(8000).set_channels(1).set_sample_width(2)
        audio.export(output_path, format="raw")

        logger.info("TTS saved to %s (%d bytes)", output_path, Path(output_path).stat().st_size)
        return True

    except Exception as exc:
        logger.error("TTS error: %s", exc)
        return False

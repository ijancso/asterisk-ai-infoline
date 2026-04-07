import io
import logging
import tempfile
import os
import subprocess
from pathlib import Path

from openai import OpenAI

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
    path = Path(audio_path)
    if not path.exists() or path.stat().st_size == 0:
        logger.warning("Audio file missing or empty: %s", audio_path)
        return ""
    try:
        mp3_path = audio_path.replace(".slin", ".mp3")
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "s16le", "-ar", "8000", "-ac", "1",
            "-i", audio_path,
            mp3_path
        ], check=True, capture_output=True)

        with open(mp3_path, "rb") as f:
            response = client.audio.transcriptions.create(
                model=WHISPER_MODEL,
                file=(mp3_path, f, "audio/mp3"),
                language="en",
            )
        os.unlink(mp3_path)
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
    try:
        mp3_path = output_path.replace(".slin", ".mp3")
        response = client.audio.speech.create(
            model="tts-1",
            voice=TTS_VOICE,
            input=text,
            response_format="mp3",
        )
        with open(mp3_path, "wb") as f:
            f.write(response.content)

        subprocess.run([
            "ffmpeg", "-y",
            "-i", mp3_path,
            "-f", "s16le", "-ar", "8000", "-ac", "1",
            output_path
        ], check=True, capture_output=True)

        os.unlink(mp3_path)
        logger.info("TTS saved to %s", output_path)
        return True
    except Exception as exc:
        logger.error("TTS error: %s", exc)
        return False

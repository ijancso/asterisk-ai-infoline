#!/usr/bin/env python3
"""
ai_infoline.py — Asterisk AGI entry point

Asterisk calls this script once per inbound call.
It handles the full conversation loop:
  1. Record caller audio
  2. Transcribe with Whisper
  3. Generate reply with GPT-4o
  4. Synthesise speech with TTS
  5. Play audio back to caller
  6. Save transcript to SQLite
"""

import logging
import os
import sys
import tempfile

# Allow imports from /app (bridge directory)
sys.path.insert(0, "/app")

class AGI:
    def __init__(self):
        self.env = {}
        while True:
            line = sys.stdin.readline().strip()
            if not line:
                break
            if ':' in line:
                key, val = line.split(':', 1)
                self.env[key.strip()] = val.strip()

    def answer(self):
        self._cmd('ANSWER')

    def stream_file(self, filename, escape_digits=''):
        self._cmd(f'STREAM FILE {filename} "{escape_digits}"')

    def record_file(self, filename, format, escape_digits, timeout, offset=0, beep='', silence=None):
        cmd = f'RECORD FILE {filename} {format} "{escape_digits}" {timeout}'
        if silence:
            cmd += f' s={silence}'
        self._cmd(cmd)

    def verbose(self, msg, level=1):
        self._cmd(f'VERBOSE "{msg}" {level}')

    def hangup(self):
        self._cmd('HANGUP')

    def _cmd(self, command):
        sys.stdout.write(command + '\n')
        sys.stdout.flush()
        return sys.stdin.readline().strip()

import database
import openai_handler
from config import LOG_LEVEL, MAX_CALL_DURATION, SILENCE_TIMEOUT

# ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("ai_infoline")

GREETING = (
    "Hello! You've reached the information line. "
    "How can I help you today?"
)

FAREWELL = (
    "Thank you for calling. Have a great day. Goodbye!"
)

MAX_TURNS = 20          # safety cap on conversation length
RECORD_SECONDS = 15     # max seconds to record per turn
SILENCE_DETECT = 2      # seconds of silence to end recording early


def play_tts(agi: AGI, text: str, label: str = "tts") -> None:
    """Synthesise text and play it to the caller via AGI."""
    with tempfile.NamedTemporaryFile(suffix=".slin", delete=False) as f:
        tmp_path = f.name

    try:
        ok = openai_handler.synthesise_speech(text, tmp_path)
        if ok:
            # Strip extension — Asterisk adds it back
            agi.stream_file(tmp_path.removesuffix(".slin"))
        else:
            logger.warning("TTS failed for label=%s, reading text directly.", label)
            agi.verbose(f"[TTS FALLBACK] {text}")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def record_caller(agi: AGI) -> str:
    """Record caller input and return path to raw audio file."""
    with tempfile.NamedTemporaryFile(suffix=".slin", delete=False) as f:
        tmp_path = f.name

    base_path = tmp_path.removesuffix(".slin")

    agi.record_file(
        filename=base_path,
        format="sln",
        escape_digits="#",
        timeout=RECORD_SECONDS * 1000,
        offset=0,
        beep="",
        silence=SILENCE_DETECT,
    )
    # Asterisk saves as base_path.sln, not base_path.slin
    actual_path = base_path + ".sln"
    return actual_path


def run(call_id: str, caller_number: str) -> None:
    agi = AGI()
    agi.answer()

    logger.info("Call started: id=%s caller=%s", call_id, caller_number)
    database.start_call(call_id, caller_number)

    conversation: list[dict] = []   # GPT message history
    transcript:   list[dict] = []   # full transcript for DB

    try:
        # ── Greeting ──────────────────────────────────────────
        play_tts(agi, GREETING, label="greeting")

        for turn_index in range(MAX_TURNS):
            # ── Record caller ──────────────────────────────────
            audio_path = record_caller(agi)
            caller_text = openai_handler.transcribe_audio(audio_path)
            os.unlink(audio_path)

            if not caller_text:
                logger.info("No speech detected, ending call.")
                play_tts(agi, "I didn't catch that. " + FAREWELL, label="no-speech")
                break

            logger.info("[Turn %d] Caller: %s", turn_index, caller_text)
            database.add_turn(call_id, turn_index, "caller", caller_text)
            transcript.append({"role": "caller", "content": caller_text})

            # Map to GPT roles
            conversation.append({"role": "user", "content": caller_text})

            # ── Check for goodbye intent ───────────────────────
            if any(w in caller_text.lower() for w in ("goodbye", "bye", "hang up", "that's all")):
                play_tts(agi, FAREWELL, label="farewell")
                break

            # ── Generate AI reply ──────────────────────────────
            reply = openai_handler.get_response(conversation)
            conversation.append({"role": "assistant", "content": reply})

            logger.info("[Turn %d] Assistant: %s", turn_index, reply)
            database.add_turn(call_id, turn_index, "assistant", reply)
            transcript.append({"role": "assistant", "content": reply})

            # ── Play reply ─────────────────────────────────────
            play_tts(agi, reply, label=f"reply-{turn_index}")

        else:
            # Hit MAX_TURNS
            play_tts(agi, FAREWELL, label="max-turns")

    except Exception as exc:
        logger.exception("Unexpected error during call %s: %s", call_id, exc)

    finally:
        summary = openai_handler.generate_summary(transcript)
        database.end_call(call_id, transcript, summary)
        logger.info("Call %s finished. Summary: %s", call_id, summary)


if __name__ == "__main__":
    # Asterisk passes call_id and caller_number as AGI arguments
    args = sys.argv[1:]
    call_id      = args[0] if len(args) > 0 else "unknown"
    caller_number = args[1] if len(args) > 1 else "unknown"

    database.init_db()
    run(call_id, caller_number)

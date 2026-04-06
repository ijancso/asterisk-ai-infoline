"""
main.py — Bridge container entrypoint

This process:
  1. Initialises the SQLite database
  2. Copies the AGI script into Asterisk's agi-bin directory
  3. Stays alive (the AGI script is spawned per-call by Asterisk)
"""

import logging
import os
import shutil
import time
from pathlib import Path

import database
from config import LOG_LEVEL

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("bridge.main")

AGI_SRC = Path("/app/agi-bin/ai_infoline.py")
AGI_DST = Path("/app/agi-bin/ai_infoline.py")


def install_agi() -> None:
    """Copy AGI script to the shared agi-bin volume that Asterisk reads."""
    AGI_DST.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(AGI_SRC, AGI_DST)
    AGI_DST.chmod(0o755)
    logger.info("AGI script installed at %s", AGI_DST)


def main() -> None:
    logger.info("Bridge starting up...")

    database.init_db()
    install_agi()

    logger.info("Ready. Waiting for Asterisk to spawn AGI calls.")

    # Keep the container alive; per-call work is done in ai_infoline.py
    while True:
        time.sleep(60)
        logger.debug("Bridge heartbeat — still alive.")


if __name__ == "__main__":
    main()

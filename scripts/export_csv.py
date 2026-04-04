#!/usr/bin/env python3
"""
export_csv.py — Export call logs to CSV

Usage:
  docker compose exec bridge python scripts/export_csv.py
  docker compose exec bridge python scripts/export_csv.py --output /app/data/export.csv
"""

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import database


def export_csv(output_path: str) -> None:
    with database.get_connection() as conn:
        rows = conn.execute("SELECT * FROM calls ORDER BY started_at DESC").fetchall()

    if not rows:
        print("No calls to export.")
        return

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "call_id", "caller_number", "started_at",
            "ended_at", "duration_seconds", "summary", "transcript_text"
        ])

        for row in rows:
            # Flatten transcript to plain text
            transcript_text = ""
            if row["transcript"]:
                turns = json.loads(row["transcript"])
                transcript_text = " | ".join(
                    f"{t['role'].upper()}: {t['content']}" for t in turns
                )

            writer.writerow([
                row["call_id"],
                row["caller_number"],
                row["started_at"],
                row["ended_at"],
                row["duration_seconds"],
                row["summary"],
                transcript_text,
            ])

    print(f"Exported {len(rows)} calls to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export call logs to CSV")
    default_out = f"/app/data/export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    parser.add_argument("--output", type=str, default=default_out)
    args = parser.parse_args()

    export_csv(args.output)

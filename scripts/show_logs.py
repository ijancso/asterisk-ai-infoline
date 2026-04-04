#!/usr/bin/env python3
"""
show_logs.py — View recent call transcripts from the terminal

Usage:
  docker compose exec bridge python scripts/show_logs.py
  docker compose exec bridge python scripts/show_logs.py --limit 5
  docker compose exec bridge python scripts/show_logs.py --call-id abc123
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import database


def show_calls(limit: int = 10, call_id: str | None = None) -> None:
    with database.get_connection() as conn:
        if call_id:
            rows = conn.execute(
                "SELECT * FROM calls WHERE call_id = ?", (call_id,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM calls ORDER BY started_at DESC LIMIT ?", (limit,)
            ).fetchall()

    if not rows:
        print("No calls found.")
        return

    for row in rows:
        print("─" * 60)
        print(f"  Call ID  : {row['call_id']}")
        print(f"  Caller   : {row['caller_number']}")
        print(f"  Started  : {row['started_at']}")
        print(f"  Duration : {row['duration_seconds']}s")
        print(f"  Summary  : {row['summary']}")

        if row["transcript"]:
            print()
            turns = json.loads(row["transcript"])
            for t in turns:
                role = "🧑 CALLER" if t["role"] == "caller" else "🤖 AI    "
                print(f"  {role}: {t['content']}")

        print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="View AI info line call logs")
    parser.add_argument("--limit", type=int, default=10, help="Number of calls to show")
    parser.add_argument("--call-id", type=str, help="Show a specific call by ID")
    args = parser.parse_args()

    show_calls(limit=args.limit, call_id=args.call_id)

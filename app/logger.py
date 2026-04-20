import json
import os
from datetime import datetime

LOG_FILE = "logs/mcq_logs.jsonl"

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)


def log_entry(status, topic, data, reason=None):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "topic": topic,
        "status": status,  # accepted / rejected / accepted_with_warnings
        "reason": reason,
        "data": data
    }
    # Append-only JSONL — one JSON object per line, no read-modify-write cycle.
    # Safe under concurrent requests; no file corruption risk.
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def read_logs() -> list[dict]:
    """Read all log entries from the JSONL file. Returns [] if file missing."""
    try:
        with open(LOG_FILE, "r") as f:
            return [json.loads(line) for line in f if line.strip()]
    except FileNotFoundError:
        return []
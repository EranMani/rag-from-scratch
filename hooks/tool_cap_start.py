#!/usr/bin/env python3
"""
tool_cap_start.py — PreToolUse hook on Agent tool.

Fires automatically before every Agent() invocation.
Sets tool_cap.json active=true and resets the counter.
This eliminates the need for the orchestrator to manually manage the cap flag.
"""

import json
import subprocess
import sys
from pathlib import Path


def git_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True
    )
    return Path(result.stdout.strip())


def read_stdin() -> dict:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except Exception:
        return {}


def main() -> int:
    try:
        cap_file = git_root() / "hooks" / "tool_cap.json"
    except Exception:
        return 0

    stdin_data = read_stdin()
    tool_input = stdin_data.get("tool_input", {})

    # Extract agent name from subagent_type, fall back to description snippet
    agent_name = (
        tool_input.get("subagent_type")
        or tool_input.get("description", "")[:20]
        or "unknown"
    )

    cap = {
        "active": True,
        "agent": agent_name,
        "count": 0,
        "limit": 25,
    }

    try:
        cap_file.write_text(json.dumps(cap, indent=2), encoding="utf-8")
    except Exception:
        pass  # fail open

    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3

import json
import os
import stat
import sys
from pathlib import Path


def load_payload():
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def find_project_env(start_dir: Path, home_dir: Path):
    for parent in [start_dir, *start_dir.parents]:
        codex_candidate = parent / ".codex" / "last30days.env"
        if codex_candidate.exists():
            return codex_candidate

        claude_candidate = parent / ".claude" / "last30days.env"
        if claude_candidate.exists():
            return claude_candidate

        if parent == home_dir or parent == parent.parent:
            break
    return None


def insecure_permissions(path: Path):
    try:
        mode = stat.S_IMODE(path.stat().st_mode)
    except OSError:
        return None

    if mode in {0o400, 0o600}:
        return None
    return f"{mode:o}"


def has_env_config():
    return bool(os.environ.get("OPENAI_API_KEY") or os.environ.get("SCRAPECREATORS_API_KEY"))


def session_start_response(payload):
    home_dir = Path(os.environ.get("HOME", str(Path.home())))
    cwd = Path(payload.get("cwd") or os.getcwd())

    project_env = find_project_env(cwd, home_dir)
    global_env = home_dir / ".config" / "last30days" / ".env"

    for candidate in (project_env, global_env):
        if candidate and candidate.exists():
            perms = insecure_permissions(candidate)
            if perms:
                return {
                    "systemMessage": (
                        f"/last30days: WARNING - {candidate} has permissions {perms} (should be 600).\n"
                        f"Fix: chmod 600 {candidate}"
                    )
                }
            return {}

    if has_env_config():
        return {}

    return {
        "systemMessage": (
            "/last30days: No API keys configured.\n\n"
            "Create .codex/last30days.env with your API keys, or use .claude/last30days.env for compatibility, "
            "or create ~/.config/last30days/.env globally. At minimum, SCRAPECREATORS_API_KEY or OPENAI_API_KEY is required."
        )
    }


def main():
    payload = load_payload()
    event_name = payload.get("hook_event_name") or (sys.argv[1] if len(sys.argv) > 1 else "")

    if event_name == "SessionStart":
        print(json.dumps(session_start_response(payload)))
        return

    print(json.dumps({}))


if __name__ == "__main__":
    main()

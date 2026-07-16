#!/usr/bin/env python3
"""
Install the bulk-extraction guard as a Claude Code GLOBAL hook.

Copies guard-bulk-extraction.py into ~/.claude/hooks/ and registers a
PreToolUse(Read) hook in ~/.claude/settings.json, so the guard applies in
every Claude Code session on this machine regardless of which project is
open — including individual Code/ projects opened directly, not just the
container root.

Idempotent: re-running refreshes the script and leaves exactly one guard
entry. Never clobbers unrelated settings (permissions, env, other hooks).

Run during Brainia init on the Claude Code surface only — Kiro and Gemini
do not use Claude Code's settings.json hooks.
"""
import json
import shutil
import sys
from pathlib import Path

HOOK_NAME = "guard-bulk-extraction.py"
STATUS = "Guarding against raw bulk-export reads"


def main() -> int:
    src = Path(__file__).resolve().parent / HOOK_NAME
    if not src.is_file():
        print(f"error: {src} not found", file=sys.stderr)
        return 1

    config = Path.home() / ".claude"
    hooks_dir = config / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    dst = hooks_dir / HOOK_NAME
    shutil.copyfile(src, dst)

    command = f'python "{dst.as_posix()}"'

    settings_path = config / "settings.json"
    settings = {}
    if settings_path.is_file():
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"error: {settings_path} is not valid JSON; not touching it",
                  file=sys.stderr)
            return 1

    hooks = settings.setdefault("hooks", {})
    pre = hooks.setdefault("PreToolUse", [])

    def points_at_guard(matcher_block) -> bool:
        return any(
            HOOK_NAME in h.get("command", "")
            for h in matcher_block.get("hooks", [])
        )

    # Idempotent: drop any prior guard entry, then add a single fresh one.
    pre[:] = [m for m in pre if not points_at_guard(m)]
    pre.append({
        "matcher": "Read",
        "hooks": [{
            "type": "command",
            "command": command,
            "statusMessage": STATUS,
        }],
    })

    settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    print(f"installed: {dst}")
    print(f"registered PreToolUse(Read) hook in {settings_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

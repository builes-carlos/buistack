#!/usr/bin/env python3
"""
SessionStart hook: injects harnessing/doctrine/condensed.md into context.

Installed by install.py as a Claude Code SessionStart hook. Reads the
condensed doctrine from disk on every session start (not baked in at install
time) so an edit to condensed.md takes effect on the next session without
reinstalling the hook.

Usage (as registered in ~/.claude/settings.json):
  python inject_doctrine.py <path-to-condensed.md>

Prints the Claude Code SessionStart hook JSON schema to stdout:
  {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "..."}}

If the condensed file is missing, prints nothing and exits 0. A missing
doctrine file should not break every session start on this machine, it
should just mean nothing gets injected. Existence is checked separately by
`install.py --check` and by harnessing-audit.
"""
import json
import sys


def main() -> int:
    if len(sys.argv) < 2:
        return 0

    condensed_path = sys.argv[1]
    try:
        with open(condensed_path, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError:
        return 0

    if not content.strip():
        return 0

    payload = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": content,
        }
    }
    print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    sys.exit(main())

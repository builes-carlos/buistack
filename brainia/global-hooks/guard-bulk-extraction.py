#!/usr/bin/env python3
"""
PreToolUse guard: blocks the Read tool on raw LLM-export artifacts.

Rationale (Model Routing): the lead session plans and synthesizes; bulk
data collection is delegated to workers that extract via a script and
write findings to a file. Pulling a 76MB export or a 1,500-line chat log
straight into a reasoning context is exactly the context-rot waste the
routing rule prevents. Text instructions alone did not hold, so this is
the hard enforcement layer.

Installed into ~/.claude by global-hooks/install.py, so it applies in every
Claude Code session on the machine regardless of which project is open, not
only the Brain vertical.

Blocks Read when the target path is an LLM-memory export:
  - any path under an "LLM memories" directory, or
  - a file named conversations.json (Claude / ChatGPT account export).

On match: deny with a message steering to worker-data-collector. The
worker must extract with a python/Bash script that WRITES findings to
/tmp (never Read the raw file), then the lead reads the small findings.

Allow-by-silence: anything that doesn't match prints nothing and exits 0,
so every other Read proceeds untouched.
"""
import json
import sys


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0  # never break tool flow on a parse error

    if payload.get("tool_name") != "Read":
        return 0

    file_path = (payload.get("tool_input") or {}).get("file_path", "") or ""
    norm = file_path.replace("\\", "/").lower()
    basename = norm.rsplit("/", 1)[-1]

    is_export = ("llm memories" in norm) or (basename == "conversations.json")
    if not is_export:
        return 0

    reason = (
        "Blocked: raw LLM-export reads must not enter a reasoning session "
        "(Model Routing). Delegate to the worker-data-collector agent: it "
        "extracts with a python/Bash script that WRITES the signal to "
        "/tmp/{slug}-findings.md and returns only the path. Then Read that "
        "small findings file and synthesize. Do not Read the raw export here."
    )
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())

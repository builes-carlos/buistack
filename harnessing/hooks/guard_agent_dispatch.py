#!/usr/bin/env python3
"""
PreToolUse hook: enforces the two agent-dispatch rules that plain doctrine text was
not enough to make anyone follow (see doctrine/universal.md, "The crew" / "An agent
lives a slice, never a task").

Installed by install.py as a Claude Code PreToolUse hook matching the Agent tool.

Contract, verified against https://code.claude.com/docs/en/hooks (fetched
2026-09-15) rather than assumed:

  - stdin carries a JSON object per PreToolUse invocation, including at least
    `session_id`, `tool_name`, and `tool_input`. For the Agent tool, `tool_input`
    carries `description`, `prompt`, `subagent_type`, and optionally `model`.
  - PreToolUse is the one event whose decision lives under `hookSpecificOutput`
    rather than a top-level `decision` field, and it is the richest of the lot:
    "four outcomes (allow, deny, ask, or defer) plus the ability to modify tool
    input before execution" (quoted from the doc's PreToolUse decision control
    section). We only ever use two of the four: `deny` and `ask`.
  - `permissionDecisionReason` reaches different audiences depending on the
    decision: "For 'deny', shown to Claude. For 'ask' ... shown to the user but
    not Claude" (same section). That is exactly the split this hook wants: the
    model check denies and the calling agent needs to see why so it can retry
    correctly; the reuse check asks and the human at the permission prompt needs
    to see why so they can decide.
  - Exit 0 with that JSON on stdout is sufficient; exit code 2 would route through
    the same `deny` path via stderr but with none of `ask`'s richer control, so
    this hook never uses it.

Two independent checks, deliberately different strengths:

  1. Model (denies). Faber, MarcoPolo and Testarossa must carry an explicit
     `model` argument on the Agent call. No judgment is involved -- a missing one
     is refused outright, with the reason saying exactly what to add. Gaudi is
     the one role allowed to run with no override, on the top of the range. This
     is not a check on which model was passed, only that one was: the doctrine
     names roles by tier, not by pinned version, and a hardcoded model name here
     would go stale the same way a hardcoded version name would in the doctrine.

  2. Reuse (asks). A per-session, append-only register under
     ~/.claude/harnessing/agent-dispatch-register/<session_id>.jsonl records every
     recognised-role dispatch this hook has let through. A second dispatch of a
     role already in that session's register does not get silently allowed or
     silently blocked: the three legitimate reasons to open a new one anyway (the
     zone changed, it is going in circles, it hung) are real and this hook cannot
     tell them apart from a redundant one, so it asks, naming the previous
     dispatch of that role, when it fired, and what its description said.

The register only ever grows within a session and is never consulted for
liveness -- this hook has no way to know whether a previously dispatched agent is
still running, and does not pretend otherwise. It records what was dispatched,
nothing more.

Fails open, always. Any exception here -- a malformed stdin payload, a corrupt or
unreadable register file, a permissions error writing it -- prints a note to
stderr and allows the call. A guard that can break the agent is worse than the
problem it guards.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROLE_NAMES = ("Gaudi", "MarcoPolo", "Faber", "Testarossa")
WORKING_MODEL_ROLES = ("Faber", "MarcoPolo", "Testarossa")

_CANON = {name.lower(): name for name in ROLE_NAMES}
_ROLE_ALTERNATION = "|".join(ROLE_NAMES)
# A dispatch description follows the convention "Faber: issue 98 distributors",
# optionally with an instance number ("Faber2: ..."), the doctrine's own examples
# for how instances of a role are told apart.
_DESC_RE = re.compile(r"^\s*(" + _ROLE_ALTERNATION + r")\d*\s*:", re.IGNORECASE)
# Fallback: scan the prompt's opening for "You are <Role>", the convention every
# subagent prompt in this stack is written with.
_PROMPT_RE = re.compile(r"\byou are\s+(" + _ROLE_ALTERNATION + r")\d*\b", re.IGNORECASE)
_PROMPT_WINDOW = 1000
_DESCRIPTION_KEPT = 300
_REASON_DESCRIPTION_SHOWN = 150

REGISTER_DIR = Path.home() / ".claude" / "harnessing" / "agent-dispatch-register"


def extract_role(description: str, prompt: str) -> str | None:
    """Read the role from the dispatch description, falling back to the prompt.

    Never guesses a role that is not one of the four -- both patterns only match
    ROLE_NAMES literally, case-insensitively.
    """
    if description:
        m = _DESC_RE.match(description)
        if m:
            return _CANON[m.group(1).lower()]
    if prompt:
        m = _PROMPT_RE.search(prompt[:_PROMPT_WINDOW])
        if m:
            return _CANON[m.group(1).lower()]
    return None


def register_path(session_id: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", session_id or "")[:200] or "unknown-session"
    return REGISTER_DIR / f"{safe}.jsonl"


def load_register(path: Path) -> list[dict]:
    """Every entry this session has recorded. Fails open: a missing, unreadable or
    partially corrupt register is treated as no known prior dispatches rather than
    as a reason to block anything.
    """
    if not path.is_file():
        return []
    entries: list[dict] = []
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue  # one corrupt line does not invalidate the rest
        if isinstance(entry, dict):
            entries.append(entry)
    return entries


def append_register(path: Path, entry: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def _trim(text: str, limit: int) -> str:
    text = text.strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def build_deny_reason(role: str) -> str:
    return (
        f'{role} must carry an explicit working-model argument on this Agent call '
        f'(e.g. model: "sonnet") -- add `model` and retry. No judgment is needed '
        f'here: the doctrine reserves the top of the range for Gaudi alone, and '
        f'{role} always runs on the working model, named on the call rather than '
        f'inherited from the lead.'
    )


def build_ask_reason(role: str, prior_entries: list[dict]) -> str:
    matches = [e for e in prior_entries if e.get("role") == role]
    last = matches[-1]
    when = last.get("timestamp") or "an earlier point this session"
    what = _trim(last.get("description") or "", _REASON_DESCRIPTION_SHOWN)
    extra = f" ({len(matches)} previous dispatches of {role} this session.)" if len(matches) > 1 else ""
    return (
        f'This session already dispatched {role} at {when}: "{what}".{extra} '
        f'An agent lives a slice, not a task -- reuse it unless the zone changed, '
        f'it is going in circles, or it hung. Dispatch a new {role} anyway?'
    )


def decide(role: str, tool_input: dict, prior_entries: list[dict]) -> tuple[str | None, str | None]:
    """Return (permissionDecision, reason). (None, None) means allow, silently."""
    if role in WORKING_MODEL_ROLES:
        model = tool_input.get("model")
        if not isinstance(model, str) or not model.strip():
            return "deny", build_deny_reason(role)

    if any(e.get("role") == role for e in prior_entries):
        return "ask", build_ask_reason(role, prior_entries)

    return None, None


def emit(decision: str, reason: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }))


def main() -> int:
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception as e:
        print(f"guard_agent_dispatch: could not parse hook input ({e}); allowing.", file=sys.stderr)
        return 0

    try:
        tool_name = payload.get("tool_name", "")
        if tool_name and tool_name != "Agent":
            return 0  # the matcher should already restrict this; be safe anyway

        tool_input = payload.get("tool_input") or {}
        description = tool_input.get("description") or ""
        prompt = tool_input.get("prompt") or ""

        role = extract_role(description, prompt)
        if role is None:
            return 0  # no recognisable role: not this hook's business

        session_id = payload.get("session_id") or ""
        path = register_path(session_id)
        prior_entries = load_register(path)

        decision, reason = decide(role, tool_input, prior_entries)

        if decision == "deny":
            emit("deny", reason)
            return 0

        entry = {
            "role": role,
            "description": description[:_DESCRIPTION_KEPT],
            "model": tool_input.get("model"),
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        try:
            append_register(path, entry)
        except OSError as e:
            print(f"guard_agent_dispatch: could not write dispatch register ({e}); allowing anyway.", file=sys.stderr)

        if decision == "ask":
            emit("ask", reason)
        return 0
    except Exception as e:
        print(f"guard_agent_dispatch: unexpected error ({e}); allowing.", file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.exit(main())

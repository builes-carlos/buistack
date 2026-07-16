# global-hooks — machine-global Claude Code guard

The guard hook lives in `~/.claude` (user-global), not in any project, so it
applies in **every** Claude Code session on the machine — the container root,
the Brain vertical, and any `Code/` project opened directly. Claude Code loads
`settings.json`/hooks only from the project you open + `~/.claude`; there is no
"subtree" scope, so global is the only way to cover directly-opened projects.

## Files

- `guard-bulk-extraction.py` — blocks raw reads of LLM-memory exports
  (`LLM memories/` paths, `conversations.json`); allow-by-silence otherwise.
- `install.py` — copies the hook into `~/.claude/hooks/` and registers a
  `PreToolUse(Read)` hook in `~/.claude/settings.json`. Idempotent; never
  clobbers unrelated settings (env, permissions, other hooks).

## Init

Brainia init runs `python global-hooks/install.py` on the Claude Code surface
(see the `onboarding` skill). Re-run anytime to refresh.

## Tradeoff

The guard is allow-by-silence — it only blocks LLM-memory exports, which exist
only in the Brain vertical, so it is a no-op everywhere else. The cost is one
python spawn per `Read` across all sessions, machine-wide.

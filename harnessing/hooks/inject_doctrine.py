#!/usr/bin/env python3
"""
SessionStart hook: injects harnessing/doctrine/condensed.md into context, and
carries install.py's own drift check -- a control nobody runs is not a control,
so this runs it on every session instead of waiting for someone to remember
`--check`.

Installed by install.py as a Claude Code SessionStart hook. Reads the
condensed doctrine from disk on every session start (not baked in at install
time) so an edit to condensed.md takes effect on the next session without
reinstalling the hook.

Drift check, entirely local, no network:

  - Auto-repairs what install.py itself owns and can fix unambiguously: the
    hook registrations (SessionStart, PreToolUse) and the skill links. Both
    are idempotent to re-run, so doing it silently on every session start is
    safe the same way re-running `install.py` by hand always was.
  - Only *reports* drift in the doctrine pointer blocks written into CLAUDE.md
    / AGENTS.md / GEMINI.md. Fixing one means knowing which directory level
    the user chose with `--path`, which this hook cannot know from its own
    cwd -- writing a pointer block into whatever project happens to be open
    would be worse than leaving the drift alone. It names the exact command
    to run instead.
  - Whatever it repairs or finds, it says: repairs are named in the injected
    context, and a short summary goes out as `systemMessage` so the person
    sees it too, not just the model.
  - Fails open: any error here -- install.py missing or unloadable, a stdin
    parse failure, anything -- is swallowed, noted to stderr, and the normal
    doctrine injection still happens. A drift check that can break session
    start is worse than the drift.

Usage (as registered in ~/.claude/settings.json):
  python inject_doctrine.py <path-to-condensed.md>

Prints the Claude Code SessionStart hook JSON schema to stdout:
  {"systemMessage": "...", (only when there is something to report)
   "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "..."}}

If the condensed file is missing, prints nothing and exits 0. A missing
doctrine file should not break every session start on this machine, it
should just mean nothing gets injected. Existence is checked separately by
`install.py --check` and by harnessing-audit.
"""
import importlib.util
import json
import sys
from pathlib import Path

DRIFT_HEADER = "harnessing install drift (auto-repaired where safe, reported where not):"


def _load_install_module(harnessing_dir: Path):
    """Dynamically load install.py from the repo this hook was installed from,
    derived from the condensed.md path passed on argv (both live under
    harnessing/). Returns None on any failure -- caller fails open.
    """
    install_path = harnessing_dir / "install.py"
    if not install_path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("harnessing_install_selfcheck", install_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    # Registering in sys.modules before exec_module matters: recent Python's
    # @dataclass looks the defining module up via sys.modules[cls.__module__],
    # and install.py's Step/HookDef dataclasses fail to define without it.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _repair_owned_items(module) -> list[str]:
    """Re-run exactly the parts of install.py this hook may fix silently: hook
    registrations and skill links. Both idempotent, so a session where nothing
    has drifted costs a handful of stat calls and produces no notes at all.
    """
    notes = []
    for step in module.install_skills(check=False) + module.install_hook(check=False):
        if step.status in ("written", "updated"):
            notes.append(f"repaired {step.name}: {step.detail}")
    return notes


def _check_doctrine_pointer(module, cwd: Path) -> str | None:
    """Report-only, never writes. Which directory owns the doctrine pointer is
    a choice made once at `harnessing-init` time (its --path); this hook only
    knows the session's cwd, not that choice, so it can search but never fix.
    """
    install_cmd = f'python "{module.HERE / "install.py"}"'
    for d in [cwd, *cwd.parents]:
        p = d / "CLAUDE.md"
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        if module.MARKER_START not in text:
            continue
        start = text.find(module.MARKER_START)
        end = text.find(module.MARKER_END)
        if end == -1 or end < start:
            return f"{p} has a doctrine start marker with no matching end marker. Run: {install_cmd} --path \"{d}\""
        current = text[start:end + len(module.MARKER_END)]
        expected = module.doctrine_pointer_block(d)
        if current.rstrip("\n") != expected.rstrip("\n"):
            return f"doctrine pointer in {p} is out of date. Run: {install_cmd} --path \"{d}\""
        return None  # found, current, nothing to report
    return f"no doctrine pointer reaches {cwd}. Run: {install_cmd} --path \"{cwd}\""


def _drift_notes(condensed_path: str) -> list[str]:
    harnessing_dir = Path(condensed_path).resolve().parent.parent
    module = _load_install_module(harnessing_dir)
    if module is None:
        return []

    notes = _repair_owned_items(module)

    cwd = Path.cwd()
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
        if payload.get("cwd"):
            cwd = Path(payload["cwd"])
    except Exception:
        pass  # stdin is a bonus for locating the doctrine pointer, not required

    doctrine_note = _check_doctrine_pointer(module, cwd)
    if doctrine_note:
        notes.append(doctrine_note)
    return notes


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

    try:
        notes = _drift_notes(condensed_path)
    except Exception as e:
        print(f"inject_doctrine: drift check failed ({e}); continuing without it.", file=sys.stderr)
        notes = []

    if notes:
        content = content.rstrip("\n") + "\n\n---\n" + DRIFT_HEADER + "\n" + "\n".join(f"- {n}" for n in notes) + "\n"

    payload = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": content,
        }
    }
    if notes:
        payload["systemMessage"] = "harnessing: " + "; ".join(notes)
    print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    sys.exit(main())

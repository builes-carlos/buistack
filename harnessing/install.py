#!/usr/bin/env python3
"""
Idempotent installer for harnessing.

Three independent operations, each safe to re-run:

  1. Skills bootstrap: copies the three harnessing skills into
                        ~/.claude/skills/ so /harnessing-init, /harnessing-audit
                        and /office-hours exist as slash commands. Claude Code
                        only, Codex and Gemini have no equivalent skill
                        mechanism in this stack, they get the doctrine pointer
                        instead (operation 2).
  2. Doctrine pointer: writes a short block into AGENTS.md, CLAUDE.md and
                        GEMINI.md at a given directory, between
                        `<!-- harnessing:start -->` / `<!-- harnessing:end -->`
                        markers, one file per agent detected on the machine.
  3. SessionStart hook: registers a Claude Code hook that injects
                        doctrine/condensed.md into context at the start of
                        every session, regardless of which directory the
                        agent was opened in.

Stdlib only. Runs on Windows and Linux.

Usage:
  python install.py --check              # report only, write nothing, exit 1 if incomplete
  python install.py                      # run all three operations at cwd
  python install.py --path <dir>         # write the doctrine pointer at <dir> instead of cwd
  python install.py --skip-skills
  python install.py --skip-doctrine
  python install.py --skip-hook

Called directly by a human once, right after cloning, to bootstrap the
skills. Called again by /harnessing-init with --path set to whatever level
the user confirmed, and by re-runs of the skill to keep the install current.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCTRINE_DIR = HERE / "doctrine"
CONDENSED_DOCTRINE = DOCTRINE_DIR / "condensed.md"
UNIVERSAL_DOCTRINE = DOCTRINE_DIR / "universal.md"
SKILLS_DIR = HERE / "skills"
HOOK_SCRIPT_SRC = HERE / "hooks" / "inject_doctrine.py"
HOOK_SCRIPT_NAME = "harnessing_inject_doctrine.py"

MARKER_START = "<!-- harnessing:start -->"
MARKER_END = "<!-- harnessing:end -->"

# agent key -> (home marker dir, file this agent reads natively)
AGENT_FILES = {
    "claude": "CLAUDE.md",
    "codex": "AGENTS.md",
    "gemini": "GEMINI.md",
}
AGENT_HOME_MARKERS = {
    "claude": ".claude",
    "codex": ".codex",
    "gemini": ".gemini",
}

SKILL_NAMES = ["harnessing-init", "harnessing-audit", "office-hours"]


@dataclass
class Step:
    name: str
    status: str  # "written" | "updated" | "skipped" | "missing" | "ok"
    detail: str

    def line(self) -> str:
        return f"  [{self.status:<8}] {self.name}: {self.detail}"


def detect_agents() -> dict[str, bool]:
    home = Path.home()
    return {agent: (home / marker).is_dir() for agent, marker in AGENT_HOME_MARKERS.items()}


def doctrine_pointer_block(target_dir: Path) -> str:
    try:
        rel = Path(
            __import__("os").path.relpath(DOCTRINE_DIR, target_dir)
        ).as_posix()
    except ValueError:
        # different drive on Windows, relpath can't cross it
        rel = DOCTRINE_DIR.as_posix()
    return (
        f"{MARKER_START}\n"
        "## harnessing doctrine\n\n"
        f"Read `{rel}/universal.md` before doing anything in this session. "
        "It governs how work gets dispatched to an agent: agent roles, when a "
        "fresh one is worth its read-the-world cost, when review needs a clean "
        "context, how much rigor a change needs.\n\n"
        "Claude Code also gets the condensed version injected automatically at "
        "session start (see harnessing/hooks/), so this pointer matters most "
        "for agents without a SessionStart hook.\n"
        f"{MARKER_END}\n"
    )


def replace_or_append_block(existing: str, block: str) -> tuple[str, bool]:
    """Return (new_content, changed). Never touches anything outside the markers."""
    start = existing.find(MARKER_START)
    end = existing.find(MARKER_END)
    if start != -1 and end != -1 and end > start:
        end_full = end + len(MARKER_END)
        new_content = existing[:start] + block.rstrip("\n") + existing[end_full:]
        return new_content, new_content != existing
    if existing and not existing.endswith("\n"):
        existing += "\n"
    new_content = existing + ("\n" if existing else "") + block
    return new_content, True


def inherits_block(target_dir: Path, filename: str) -> Path | None:
    """Return the ancestor that already carries the doctrine block, if any.

    AGENTS.md and CLAUDE.md load the one in the working directory plus every
    parent, so a block at the container level already reaches every directory
    under it. Writing a second one further down would duplicate a rule across
    two layers, which is exactly what the doctrine forbids and what the audit
    is meant to catch. Reporting it as missing sends the reader to create the
    duplication.
    """
    for ancestor in target_dir.parents:
        candidate = ancestor / filename
        if candidate.is_file() and MARKER_START in candidate.read_text(encoding="utf-8"):
            return candidate
    return None


def install_doctrine_pointer(target_dir: Path, agents: dict[str, bool], check: bool) -> list[Step]:
    steps: list[Step] = []
    if not UNIVERSAL_DOCTRINE.is_file():
        steps.append(Step("doctrine pointer", "missing",
                           f"{UNIVERSAL_DOCTRINE} does not exist, nothing to point to"))
        return steps

    block = doctrine_pointer_block(target_dir)
    for agent, present in agents.items():
        if not present:
            continue
        filename = AGENT_FILES[agent]
        path = target_dir / filename
        existing = path.read_text(encoding="utf-8") if path.is_file() else ""

        if MARKER_START not in existing:
            inherited = inherits_block(target_dir, filename)
            if inherited is not None:
                steps.append(Step(filename, "ok",
                                   f"doctrine block inherited from {inherited}"))
                continue

        new_content, changed = replace_or_append_block(existing, block)

        if not changed:
            steps.append(Step(filename, "ok", "doctrine block already current"))
            continue

        if check:
            reason = "would create" if not path.is_file() else "would update"
            steps.append(Step(filename, "missing", f"{reason} doctrine block at {path}"))
            continue

        path.write_text(new_content, encoding="utf-8")
        steps.append(Step(filename, "written" if not existing else "updated",
                           f"doctrine block at {path}"))
    return steps


def install_skills(check: bool) -> list[Step]:
    steps: list[Step] = []
    claude_skills_dir = Path.home() / ".claude" / "skills"
    if not (Path.home() / ".claude").is_dir():
        steps.append(Step("skills", "skipped", "no ~/.claude on this machine"))
        return steps

    for name in SKILL_NAMES:
        src = SKILLS_DIR / name
        if not src.is_dir():
            steps.append(Step(name, "missing", f"{src} not found in this clone"))
            continue

        dest = claude_skills_dir / name
        needs_write = True
        if dest.is_dir():
            same = all(
                (dest / f.name).is_file()
                and (dest / f.name).read_text(encoding="utf-8") == f.read_text(encoding="utf-8")
                for f in src.glob("*.md")
            )
            needs_write = not same

        if not needs_write:
            steps.append(Step(name, "ok", f"already up to date at {dest}"))
            continue

        if check:
            steps.append(Step(name, "missing", f"would copy to {dest}"))
            continue

        dest.mkdir(parents=True, exist_ok=True)
        for f in src.glob("*.md"):
            shutil.copyfile(f, dest / f.name)
        steps.append(Step(name, "written", f"copied to {dest}"))
    return steps


def install_hook(check: bool) -> list[Step]:
    steps: list[Step] = []
    claude_dir = Path.home() / ".claude"
    if not claude_dir.is_dir():
        steps.append(Step("SessionStart hook", "skipped", "no ~/.claude on this machine"))
        return steps

    if not HOOK_SCRIPT_SRC.is_file():
        steps.append(Step("SessionStart hook", "missing", f"{HOOK_SCRIPT_SRC} not found"))
        return steps
    if not CONDENSED_DOCTRINE.is_file():
        steps.append(Step("SessionStart hook", "missing",
                           f"{CONDENSED_DOCTRINE} does not exist, nothing to inject"))
        return steps

    hooks_dir = claude_dir / "hooks"
    dst = hooks_dir / HOOK_SCRIPT_NAME
    script_current = dst.is_file() and dst.read_text(encoding="utf-8") == HOOK_SCRIPT_SRC.read_text(encoding="utf-8")

    settings_path = claude_dir / "settings.json"
    settings: dict = {}
    if settings_path.is_file():
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            steps.append(Step("SessionStart hook", "missing",
                               f"{settings_path} is not valid JSON, not touching it"))
            return steps

    command = f'python "{dst.as_posix()}" "{CONDENSED_DOCTRINE.as_posix()}"'

    def points_at_hook(block: dict) -> bool:
        return any(HOOK_SCRIPT_NAME in h.get("command", "") for h in block.get("hooks", []))

    session_start = settings.get("hooks", {}).get("SessionStart", [])
    already_registered = any(points_at_hook(b) for b in session_start)

    if script_current and already_registered:
        steps.append(Step("SessionStart hook", "ok", f"registered and current at {dst}"))
        return steps

    if check:
        steps.append(Step("SessionStart hook", "missing",
                           "would install/register the harnessing doctrine hook"))
        return steps

    hooks_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(HOOK_SCRIPT_SRC, dst)

    hooks = settings.setdefault("hooks", {})
    starts = hooks.setdefault("SessionStart", [])
    starts[:] = [b for b in starts if not points_at_hook(b)]
    starts.append({"hooks": [{"type": "command", "command": command}]})

    settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    steps.append(Step("SessionStart hook", "written", f"installed at {dst}, registered in {settings_path}"))
    return steps


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="report only, write nothing")
    parser.add_argument("--path", type=Path, default=Path.cwd(),
                         help="directory to write the doctrine pointer at (default: cwd)")
    parser.add_argument("--skip-skills", action="store_true")
    parser.add_argument("--skip-doctrine", action="store_true")
    parser.add_argument("--skip-hook", action="store_true")
    args = parser.parse_args()

    agents = detect_agents()
    detected = [a for a, present in agents.items() if present]
    print(f"Agents detected on this machine: {', '.join(detected) if detected else 'none'}")

    all_steps: list[Step] = []
    if not args.skip_skills:
        all_steps += install_skills(args.check)
    if not args.skip_doctrine:
        all_steps += install_doctrine_pointer(args.path.resolve(), agents, args.check)
    if not args.skip_hook:
        all_steps += install_hook(args.check)

    print()
    for step in all_steps:
        print(step.line())

    incomplete = [s for s in all_steps if s.status in ("missing", "skipped")]
    if args.check:
        if incomplete:
            print(f"\n--check: {len(incomplete)} item(s) not installed or out of date.")
            return 1
        print("\n--check: install is complete.")
        return 0

    hard_missing = [s for s in all_steps if s.status == "missing"]
    if hard_missing:
        print(f"\n{len(hard_missing)} item(s) could not be installed. See detail above.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

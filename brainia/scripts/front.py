#!/usr/bin/env python3
"""
Manage Brainia front activation.

A front is one area of a person's life (fronts/<id>.md). A front may own
skills, staged at fronts/<id>/skills/<name>/. Claude Code only discovers
skills under .claude/skills/, so activating a front copies its staged
skills there; deactivating removes exactly what activation installed.

Pure standard library. No third-party imports. Works on Windows and POSIX.

Commands:
  list                    List every front pack and its basic facts.
  status                  Show active fronts, installed skills, and drift.
  activate <front_id>     Copy a front's staged skills into .claude/skills/.
  deactivate <front_id>   Remove a front's installed skills.

Run `python scripts/front.py <command> --help` for command-specific options.
"""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
FRONTS_DIR = REPO_ROOT / "fronts"
CLAUDE_SKILLS_DIR = REPO_ROOT / ".claude" / "skills"
STATE_FILE = FRONTS_DIR / ".activated.json"
# Default: "the container is the parent of this repo's own directory." This
# is only correct when this checkout IS the container's Brain/ instance
# (repo directory literally named "Brain", sitting directly under the
# container root). Override with --container when it is not. See
# resolve_container() / container_notes().
DEFAULT_CONTAINER_DIR = REPO_ROOT.parent


# --------------------------------------------------------------------------
# Frontmatter parsing
# --------------------------------------------------------------------------

def parse_frontmatter(text):
    """Parse the flat `key: value` / `key: [a, b, c]` frontmatter this repo
    actually uses. Not a general YAML parser. Raises ValueError on anything
    it does not understand."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing opening '---'")
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        raise ValueError("missing closing '---'")

    data = {}
    for raw_line in lines[1:end]:
        line = raw_line.strip()
        if not line:
            continue
        if ":" not in line:
            raise ValueError(f"cannot parse frontmatter line: {raw_line!r}")
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if not key:
            raise ValueError(f"empty key in frontmatter line: {raw_line!r}")
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            if not inner:
                data[key] = []
            else:
                data[key] = [item.strip().strip("'\"") for item in inner.split(",")]
        else:
            data[key] = value.strip("'\"")
    return data


def load_pack(path):
    """Load one front pack. Returns a dict always containing 'file' and
    'id_hint' (filename stem). On success also contains parsed fields and
    'body' (raw text after the closing '---'). On failure contains 'error'."""
    result = {"file": path, "id_hint": path.stem}
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        result["error"] = f"cannot read file: {exc}"
        return result

    try:
        fm = parse_frontmatter(text)
    except ValueError as exc:
        result["error"] = str(exc)
        return result

    if "front_id" not in fm or not fm["front_id"]:
        result["error"] = "frontmatter missing required field: front_id"
        return result

    lines = text.splitlines()
    body_start = None
    seen_dashes = 0
    for i, line in enumerate(lines):
        if line.strip() == "---":
            seen_dashes += 1
            if seen_dashes == 2:
                body_start = i + 1
                break
    body = "\n".join(lines[body_start:]) if body_start is not None else ""

    result.update(
        front_id=fm["front_id"],
        display_name=fm.get("display_name", fm["front_id"]),
        aliases=fm.get("aliases", []),
        sibling=fm.get("sibling", ""),
        writes_to=fm.get("writes_to", []),
        methodology=fm.get("methodology", "none"),
        reads_back=fm.get("reads_back", []),
        skills=fm.get("skills", []),
        profiles=fm.get("profiles", []),
        integrations=fm.get("integrations", []),
        body=body,
    )
    return result


def load_all_packs():
    """Return {front_id_or_filename_stem: pack_dict} for every fronts/*.md
    that does not start with '_'."""
    packs = {}
    if not FRONTS_DIR.is_dir():
        return packs
    for path in sorted(FRONTS_DIR.glob("*.md")):
        if path.name.startswith("_"):
            continue
        pack = load_pack(path)
        key = pack.get("front_id", pack["id_hint"])
        packs[key] = pack
    return packs


# --------------------------------------------------------------------------
# State file
# --------------------------------------------------------------------------

def load_state():
    if not STATE_FILE.is_file():
        return {}
    try:
        raw = STATE_FILE.read_text(encoding="utf-8-sig")
    except OSError as exc:
        print(f"error: cannot read {rel(STATE_FILE)}: {exc}", file=sys.stderr)
        sys.exit(1)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"error: {rel(STATE_FILE)} is not valid JSON ({exc}).", file=sys.stderr)
        print(
            "  to recover: fix the file by hand, or delete it and re-run "
            "'activate' for each front that should be active.",
            file=sys.stderr,
        )
        sys.exit(1)
    if not isinstance(data, dict):
        print(f"error: {rel(STATE_FILE)} does not contain a JSON object.", file=sys.stderr)
        print(
            "  to recover: fix the file by hand, or delete it and re-run "
            "'activate' for each front that should be active.",
            file=sys.stderr,
        )
        sys.exit(1)
    for front_id, names in data.items():
        if not isinstance(names, list) or not all(isinstance(n, str) for n in names):
            print(
                f"error: {rel(STATE_FILE)} has a malformed entry for '{front_id}' "
                "(expected a list of skill-name strings).",
                file=sys.stderr,
            )
            print(
                "  to recover: fix the file by hand, or delete it and re-run "
                "'activate' for each front that should be active.",
                file=sys.stderr,
            )
            sys.exit(1)
    return data


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {k: sorted(v) for k, v in state.items()}
    STATE_FILE.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def rel(path):
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def sibling_exists(pack, container):
    sib = pack.get("sibling", "")
    if not sib:
        return False
    name = sib.rstrip("/\\")
    if not name:
        return False
    return (container / name).is_dir()


def resolve_container(explicit_container):
    """Return (container_path, explicit: bool). Explicit means the caller
    passed --container and it should be trusted outright."""
    if explicit_container:
        return Path(explicit_container).expanduser().resolve(), True
    return DEFAULT_CONTAINER_DIR, False


def container_notes(packs, container, explicit):
    """Decide whether the default container resolution looks trustworthy.
    Returns (note_lines, sibling_known: bool). When sibling_known is False,
    callers must report sibling status as 'unknown', not 'no' -- a 'no' is
    a claim, 'unknown' is the truth."""
    if explicit:
        return [], True

    # Identify the brain by its CONTENTS, never by its name. The README shows it
    # cloned as `Brain/`, but the folder name belongs to the user: a real instance
    # may be `brainia-alex/`, `mi-cerebro/`, anything at all.
    #
    # The discriminator is the profile, not the vault directory: this framework
    # repo also ships a `vault/` scaffold, so a bare vault check would make the
    # framework checkout claim to be an instance and go back to asserting a false
    # `sibling=no`. An onboarded instance is the one with MY-PROFILE.md.
    if (REPO_ROOT / "vault" / "00-inbox" / "MY-PROFILE.md").is_file():
        return [], True

    ok_packs = [p for p in packs.values() if "error" not in p]
    any_sibling = any(sibling_exists(p, container) for p in ok_packs)
    if any_sibling:
        return [], True

    note = (
        f"note: this checkout does not look like a container instance "
        f"(resolved container: {container}). Front siblings cannot be "
        f"verified. Use --container <path> to point at a real container."
    )
    return [note], False


def dirs_equal(a: Path, b: Path) -> bool:
    """True if two directories contain the same relative files with the
    same byte content."""
    if not a.is_dir() or not b.is_dir():
        return False
    a_files = sorted(p.relative_to(a).as_posix() for p in a.rglob("*") if p.is_file())
    b_files = sorted(p.relative_to(b).as_posix() for p in b.rglob("*") if p.is_file())
    if a_files != b_files:
        return False
    for name in a_files:
        if (a / name).read_bytes() != (b / name).read_bytes():
            return False
    return True


def detect_methodology(pack):
    """Detect (never install) an external methodology tool. Returns
    (detected: bool, message_lines: list[str])."""
    methodology = pack.get("methodology", "none")
    lines = []
    if not methodology or methodology == "none":
        return None, lines

    home_skills = Path.home() / ".claude" / "skills"
    pattern = f"{methodology}-*"
    matches = sorted(home_skills.glob(pattern)) if home_skills.is_dir() else []
    detected = len(matches) > 0

    lines.append(f"Methodology: {methodology}")
    if detected:
        found = ", ".join(m.name for m in matches)
        lines.append(f"  detected: yes ({found} in {home_skills})")
    else:
        lines.append(f"  detected: no (looked for '{pattern}' in {home_skills})")
        body = pack.get("body", "")
        repo_match = re.search(r"\*\*Repo location:\*\*\s*(.+)", body)
        install_match = re.search(r"\*\*Install:\*\*\s*(.+)", body)
        if repo_match:
            lines.append(f"  repo location: {repo_match.group(1).strip()}")
        if install_match:
            lines.append(f"  install: {install_match.group(1).strip()}")
        if not repo_match and not install_match:
            lines.append(
                f"  no install instructions found in {rel(pack['file'])}; "
                "see that pack for details"
            )
    lines.append("  Brainia does not install or run this tool.")
    return detected, lines


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------

def cmd_list(args):
    packs = load_all_packs()
    state = load_state()
    if not packs:
        print("no front packs found in fronts/")
        return 0

    container, explicit = resolve_container(args.container)
    notes, sibling_known = container_notes(packs, container, explicit)
    for note in notes:
        print(note)

    # A person who does not have a front never sees it. Default view shows
    # only fronts whose sibling actually resolves, plus anything currently
    # active. --all is the deliberate "browse what's available" escape
    # hatch. When the container can't be resolved at all, filtering would
    # hide everything for the wrong reason, so fall back to showing all
    # packs unfiltered instead.
    effective_all = args.all or not sibling_known
    if not sibling_known:
        print("note: showing all packs unfiltered because the container could not be resolved.")

    had_error = False
    shown_rows = 0
    for key in sorted(packs):
        pack = packs[key]
        if "error" in pack:
            had_error = True
            print(f"{key}: ERROR in {rel(pack['file'])}: {pack['error']}")
            continue

        active = pack["front_id"] in state
        if sibling_known:
            has_sibling = sibling_exists(pack, container)
            sib_str = "yes" if has_sibling else "no"
            yours = has_sibling or active
        else:
            sib_str = "unknown"
            yours = True  # can't tell in fallback mode; don't mark anything

        if not effective_all and not yours:
            continue

        marker = "" if yours else " [available, not yours]"
        shown_rows += 1
        print(
            f"{pack['front_id']}: "
            f"sibling={sib_str} "
            f"skills={len(pack['skills'])} "
            f"methodology={pack['methodology']} "
            f"active={'yes' if active else 'no'}"
            f"{marker}"
        )

    if shown_rows == 0 and not had_error and not effective_all:
        print(
            "no fronts detected in this container. Use --all to browse "
            "every available front, or see fronts/_template.md to add one."
        )

    return 1 if had_error else 0


def cmd_status(args):
    state = load_state()
    packs = load_all_packs()

    if not state:
        print("no fronts are active")
        return 0

    drift_found = False
    for front_id in sorted(state):
        skills = state[front_id]
        print(f"{front_id}: active, {len(skills)} skill(s) installed")
        pack = packs.get(front_id)
        for name in sorted(skills):
            installed_path = CLAUDE_SKILLS_DIR / name
            if not installed_path.is_dir():
                print(f"  DRIFT: {name} recorded as installed but missing from .claude/skills/")
                drift_found = True
                continue
            if pack is None:
                print(f"  {name}: installed (pack fronts/{front_id}.md no longer resolvable, cannot compare)")
                continue
            staged_path = FRONTS_DIR / front_id / "skills" / name
            if not staged_path.is_dir():
                print(f"  DRIFT: {name} installed but staged source fronts/{front_id}/skills/{name}/ is missing")
                drift_found = True
                continue
            if dirs_equal(installed_path, staged_path):
                print(f"  {name}: installed, matches staged source")
            else:
                print(f"  DRIFT: {name} installed but differs from staged source")
                drift_found = True
    return 1 if drift_found else 0


def cmd_activate(args):
    packs = load_all_packs()
    front_id = args.front_id
    pack = packs.get(front_id)

    if pack is None or "error" in pack:
        valid_ids = sorted(k for k, p in packs.items() if "error" not in p)
        if pack is not None:
            print(f"error: front pack '{front_id}' has a parse error: {pack['error']}", file=sys.stderr)
        else:
            print(f"error: unknown front id '{front_id}'", file=sys.stderr)
        print(f"valid ids: {', '.join(valid_ids) if valid_ids else '(none)'}", file=sys.stderr)
        return 1

    skills = pack["skills"]
    staged_root = FRONTS_DIR / front_id / "skills"
    missing = [s for s in skills if not (staged_root / s / "SKILL.md").is_file()]
    if missing:
        print(f"error: front '{front_id}' is missing staged skill(s), aborting without copying anything:", file=sys.stderr)
        for name in missing:
            print(f"  missing: {rel(staged_root / name / 'SKILL.md')}", file=sys.stderr)
        return 1

    state = load_state()
    owner_of = {}
    for fid, names in state.items():
        if fid == front_id:
            continue
        for name in names:
            owner_of[name] = fid

    collisions = []
    for name in skills:
        target = CLAUDE_SKILLS_DIR / name
        if not target.exists():
            continue
        if name in state.get(front_id, []):
            continue  # own previous install, safe to refresh
        owner = owner_of.get(name)
        if owner:
            collisions.append((name, f"belongs to front '{owner}'"))
        else:
            collisions.append((name, "collides with a core skill or an untracked directory"))

    if collisions and not args.force:
        print(f"error: activating '{front_id}' would overwrite skill(s) it does not own:", file=sys.stderr)
        for name, reason in collisions:
            print(f"  {name}: {reason}", file=sys.stderr)
        print("re-run with --force to override deliberately", file=sys.stderr)
        return 1

    if collisions and args.force:
        for name, reason in collisions:
            print(f"warning: --force overriding collision on '{name}' ({reason})")

    verb = "would install" if args.dry_run else "installed"
    for name in skills:
        src = staged_root / name
        dst = CLAUDE_SKILLS_DIR / name
        print(f"{verb}: {rel(src)} -> {rel(dst)}")

    if not args.dry_run:
        CLAUDE_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
        for name in skills:
            src = staged_root / name
            dst = CLAUDE_SKILLS_DIR / name
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
        state[front_id] = sorted(skills)
        save_state(state)
        print(f"recorded: {rel(STATE_FILE)}")

    detected, methodology_lines = detect_methodology(pack)
    for line in methodology_lines:
        print(line)

    return 0


def cmd_deactivate(args):
    front_id = args.front_id
    state = load_state()

    if front_id not in state:
        print(f"front '{front_id}' is not active, nothing to do")
        return 0

    skills = state[front_id]
    staged_root = FRONTS_DIR / front_id / "skills"
    kept = []
    had_refusal = False

    verb_remove = "would remove" if args.dry_run else "removed"

    for name in sorted(skills):
        target = CLAUDE_SKILLS_DIR / name
        if not target.exists():
            print(f"{name}: already absent from .claude/skills/, skipping")
            continue

        staged = staged_root / name
        if staged.is_dir() and not dirs_equal(target, staged) and not args.force:
            print(
                f"refusing to remove '{name}': installed copy differs from staged source "
                f"(local edits would be lost); re-run with --force to override"
            )
            kept.append(name)
            had_refusal = True
            continue

        print(f"{verb_remove}: {rel(target)}")
        if not args.dry_run:
            shutil.rmtree(target)

    if not args.dry_run:
        if kept:
            state[front_id] = sorted(kept)
        else:
            del state[front_id]
        save_state(state)
        print(f"recorded: {rel(STATE_FILE)}")

    return 1 if had_refusal else 0


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(
        prog="front.py",
        description="Manage Brainia front activation (staged skills -> .claude/skills/).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    container_help = (
        "Path to the container to check front sibling folders against. "
        "Defaults to the parent of this repo's own directory, which is only "
        "correct when this checkout IS the container's Brain/ instance."
    )

    p_list = sub.add_parser("list", help="List fronts the container actually has: sibling, skills, methodology, active state")
    p_list.add_argument("--container", help=container_help)
    p_list.add_argument(
        "--all",
        action="store_true",
        help="Show every pack on disk, including ones with no sibling here, marked as available-but-not-yours",
    )

    p_status = sub.add_parser("status", help="Show active fronts, installed skills, and drift from staged source")
    p_status.add_argument("--container", help=container_help)

    p_activate = sub.add_parser("activate", help="Activate a front: copy its staged skills into .claude/skills/")
    p_activate.add_argument("front_id", help="Front id, e.g. 'work'")
    p_activate.add_argument("--dry-run", action="store_true", help="Print the plan without touching disk")
    p_activate.add_argument("--force", action="store_true", help="Override a skill-directory collision deliberately")
    p_activate.add_argument("--container", help=container_help)

    p_deactivate = sub.add_parser("deactivate", help="Deactivate a front: remove only the skills it installed")
    p_deactivate.add_argument("front_id", help="Front id, e.g. 'work'")
    p_deactivate.add_argument("--dry-run", action="store_true", help="Print the plan without touching disk")
    p_deactivate.add_argument("--force", action="store_true", help="Remove even if the installed copy has local edits")
    p_deactivate.add_argument("--container", help=container_help)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "list":
        return cmd_list(args)
    if args.command == "status":
        return cmd_status(args)
    if args.command == "activate":
        return cmd_activate(args)
    if args.command == "deactivate":
        return cmd_deactivate(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())

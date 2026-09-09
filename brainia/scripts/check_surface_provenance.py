#!/usr/bin/env python3
"""Catch a Claude skill that changed without its other surfaces being reviewed.

Name parity, which the surface validator already checks, catches a skill that was
renamed or never ported. It does not catch the case that matters more: a skill that
gains a step in `.claude/skills/` while the Gemini and Kiro versions keep describing
the old behaviour. The counts stay right, the names stay right, and the adaptations
quietly become wrong.

A diff cannot settle it, because these are deliberately different: 354 lines for
Claude, 105 for Kiro, 47 for Gemini. They are adaptations, not copies, so being
different is the correct state.

What can be settled is whether anyone looked. Each adaptation records the sha256 of the
source it was ported from. When the source changes, the recorded hash stops matching
and this fails, naming what changed and what has to be re-read. Fixing it means
reviewing the adaptation and re-stamping with --update, which is a deliberate act
rather than something that happens by forgetting.

Stdlib only, so it runs in CI with no install step.
"""

import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MANIFEST = ROOT / ".surface-provenance.json"

# Kiro calls it brainia-update; every other surface calls it update-brainia.
KIRO_ALIASES = {"update-brainia": "update"}


def sha(path: pathlib.Path) -> str:
    """Hash the content, not the bytes on this particular disk.

    Line endings are not content. A checkout on Windows with core.autocrlf on holds
    CRLF while CI holds LF, so hashing raw bytes makes every stamp look stale the
    moment the check leaves the machine that wrote it. This check caught exactly that
    on its first CI run, which is the argument for having it.
    """
    text = path.read_bytes().decode("utf-8", "replace")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def adaptations() -> dict[str, pathlib.Path]:
    """Map each adaptation's path to the Claude skill it was ported from."""
    found = {}
    for src in sorted((ROOT / ".claude/skills").glob("*/SKILL.md")):
        name = src.parent.name
        kiro_name = KIRO_ALIASES.get(name, name)
        for candidate in (
            ROOT / f".gemini/skills/{name}.md",
            ROOT / f".gemini/commands/{name}.toml",
            ROOT / f".kiro/powers/brainia-{kiro_name}/POWER.md",
        ):
            if candidate.is_file():
                found[str(candidate.relative_to(ROOT)).replace("\\", "/")] = src
    return found


def main() -> int:
    update = "--update" in sys.argv
    pairs = adaptations()

    if not pairs:
        print("no adaptations found, nothing to check")
        return 0

    stored = {}
    if MANIFEST.is_file():
        stored = json.loads(MANIFEST.read_text(encoding="utf-8"))

    stale, unstamped, fresh = [], [], {}
    for adaptation, src in sorted(pairs.items()):
        current = sha(src)
        rel_src = str(src.relative_to(ROOT)).replace("\\", "/")
        fresh[adaptation] = {"ported_from": rel_src, "source_sha256": current}
        recorded = stored.get(adaptation, {}).get("source_sha256")
        if recorded is None:
            unstamped.append(adaptation)
        elif recorded != current:
            stale.append((adaptation, rel_src))

    if update:
        MANIFEST.write_text(json.dumps(fresh, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")
        print(f"stamped {len(fresh)} adaptations against their sources")
        return 0

    if unstamped:
        print("These adaptations carry no provenance stamp:")
        for a in unstamped:
            print(f"  {a}")
        print("Run: python scripts/check_surface_provenance.py --update")
        return 1

    if stale:
        print("A Claude skill changed after its adaptation was last reviewed.")
        print("Read the adaptation, carry over whatever the change means for it, then")
        print("re-stamp with: python scripts/check_surface_provenance.py --update")
        print()
        for adaptation, src in stale:
            print(f"  {src} changed, so {adaptation} needs a look")
        return 1

    print(f"provenance OK: {len(pairs)} adaptations, each stamped against a source "
          f"that has not changed since")
    return 0


if __name__ == "__main__":
    sys.exit(main())

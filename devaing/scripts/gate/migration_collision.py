#!/usr/bin/env python3
"""devaing gate: fail if this branch introduces a migration number already used
on the target branch, under a different file.

Only applies to the numbered-SQL-file convention (migrations/NNN_name.sql), the
one that actually collided in practice: two people, each numbering from their
own local checkout, land the same number for different migrations. Projects
using timestamp-based migration tools (Prisma, Alembic autogenerate, etc.) don't
have this failure mode -- the check is inert for them (exits 0, "not applicable").

Compares HEAD's migrations/ tree against the freshly-fetched origin/<branch>
tree, not a commit-range diff -- collision is a property of "what's on main
right now", not of this branch's own history.

No third-party dependencies (stdlib only).
"""
import os
import re
import subprocess
import sys

MIGRATIONS_DIR = os.environ.get("DEVAING_GATE_MIGRATIONS_DIR", "migrations")
NUMBERED_RE = re.compile(r"^(\d+)_.*\.sql$")


def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def ls_tree(ref):
    code, out, _ = run(["git", "ls-tree", "-r", "--name-only", ref, "--", MIGRATIONS_DIR])
    if code != 0:
        return []
    return [f for f in out.splitlines() if f]


def numbered(files):
    result = {}
    for f in files:
        base = f.rsplit("/", 1)[-1]
        m = NUMBERED_RE.match(base)
        if m:
            result[m.group(1)] = f
    return result


def main():
    branch = os.environ.get("DEVAING_GATE_BRANCH", "main")

    head_files = ls_tree("HEAD")
    head_numbered = numbered(head_files)
    if not head_numbered:
        print(f"migration_collision: no numbered migrations under {MIGRATIONS_DIR}/ -- not applicable.")
        return 0

    subprocess.run(["git", "fetch", "origin", branch], capture_output=True)
    base_files = ls_tree(f"origin/{branch}")
    base_numbered = numbered(base_files)

    collisions = []
    for number, path in head_numbered.items():
        base_path = base_numbered.get(number)
        if base_path and base_path != path:
            collisions.append((number, path, base_path))

    if not collisions:
        print("migration_collision OK.")
        return 0

    print("migration_collision FAILED:")
    for number, head_path, base_path in collisions:
        print(f"  migration number {number} used by both:")
        print(f"    this branch: {head_path}")
        print(f"    origin/{branch}: {base_path}")
    print()
    print("  Renumber this branch's migration(s) against origin/{}, not your local checkout.".format(branch))
    return 1


if __name__ == "__main__":
    sys.exit(main())

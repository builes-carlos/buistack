#!/usr/bin/env python3
"""devaing gate: fail if domain code changed without a doc update in the same range.

Instruction (a rule in AGENTS.md or a step inside a skill) is not enforcement --
it is skipped the moment a change doesn't go through the skill that carries it.
This script is the backstop: it runs in CI, with no agent session present, and
fails the build if a change touches non-trivial domain code but never touches
CONTEXT.md, AGENTS.md, or docs/**.

Range resolution:
  - DEVAING_GATE_BASE_SHA env var (set by the workflow for push events, from
    github.event.before) if present and not the all-zero SHA.
  - Otherwise `git merge-base origin/<branch> HEAD` (covers pull_request events
    and local testing).

Escape hatch: any commit message in range containing "[skip-docs-check]" skips
the check entirely -- legitimate doc-free changes (typo fixes, pure refactors)
should not have to fight the gate every time.

No third-party dependencies (stdlib only).
"""
import os
import re
import subprocess
import sys

LINE_FLOOR = int(os.environ.get("DEVAING_GATE_LINE_FLOOR", "10"))
SKIP_MARKER = "[skip-docs-check]"
ZERO_SHA = "0" * 40

DOC_RE = re.compile(r"(^|/)(CONTEXT\.md|AGENTS\.md)$|(^|/)docs/")
TEST_RE = re.compile(r"([._-]test|[._-]spec|/tests?/|/__tests__/)", re.IGNORECASE)
CONFIG_RE = re.compile(
    r"^(\.github/|package(-lock)?\.json$|.*\.lock$|tsconfig.*\.json$|"
    r"\.env(\.|$)|\.gitignore$|eslint|prettier|README\.md$|"
    r"CHECKPOINTS\.md$|\.devaing\.md$)"
)


def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def resolve_base(branch):
    base_sha = os.environ.get("DEVAING_GATE_BASE_SHA", "").strip()
    if base_sha and base_sha != ZERO_SHA:
        return base_sha

    subprocess.run(["git", "fetch", "origin", branch], capture_output=True)
    code, out, _ = run(["git", "merge-base", f"origin/{branch}", "HEAD"])
    if code != 0 or not out:
        return None
    return out


def classify(path):
    if DOC_RE.search(path):
        return "doc"
    if TEST_RE.search(path):
        return "test"
    if CONFIG_RE.search(path):
        return "config"
    return "domain"


def main():
    branch = os.environ.get("DEVAING_GATE_BRANCH", "main")
    base = resolve_base(branch)
    if base is None:
        print("feed_gate: could not resolve a base ref (new branch push?) -- skipping.")
        return 0

    code, messages, _ = run(["git", "log", f"{base}..HEAD", "--format=%B"])
    if code == 0 and SKIP_MARKER in messages:
        print(f"feed_gate: {SKIP_MARKER} found in range -- skipping.")
        return 0

    code, changed, _ = run(["git", "diff", "--name-only", f"{base}..HEAD"])
    if code != 0:
        print(f"feed_gate: could not diff {base}..HEAD -- skipping.")
        return 0
    changed_files = [f for f in changed.splitlines() if f]
    if not changed_files:
        print("feed_gate: no changed files in range.")
        return 0

    buckets = {f: classify(f) for f in changed_files}
    doc_touched = any(b == "doc" for b in buckets.values())
    domain_files = [f for f, b in buckets.items() if b == "domain"]
    if not domain_files or doc_touched:
        print("feed_gate OK.")
        return 0

    code, numstat, _ = run(["git", "diff", "--numstat", f"{base}..HEAD"])
    domain_lines = 0
    if code == 0:
        for line in numstat.splitlines():
            parts = line.split("\t")
            if len(parts) != 3:
                continue
            added, removed, path = parts
            if path not in domain_files:
                continue
            added = int(added) if added.isdigit() else 0
            removed = int(removed) if removed.isdigit() else 0
            domain_lines += added + removed

    if domain_lines < LINE_FLOOR:
        print(f"feed_gate OK ({domain_lines} domain lines, under floor of {LINE_FLOOR}).")
        return 0

    print("feed_gate FAILED:")
    print(f"  {domain_lines} domain lines changed across {len(domain_files)} file(s),")
    print("  but no CONTEXT.md, AGENTS.md, or docs/** file changed in the same range:")
    for f in domain_files:
        print(f"    {f}")
    print()
    print("  Update CONTEXT.md (or the relevant docs/features/*.md) in this change,")
    print(f"  or add {SKIP_MARKER} to a commit message if this genuinely needs no doc update.")
    return 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Refuse to publish anything that names what must stay private.

The strings come from the environment, never from this file. A public repository
cannot carry the list of private names it is meant to keep out, because the list would
be the leak. Unset, this passes and says so, so a fork is never blocked by a list it
cannot see.

Three surfaces get scanned, and the first version of this check missed two of them:

**Every blob in history, not the working tree.** Checking only the current files means
a name committed on Monday and deleted on Tuesday reports clean while it stays alive
one commit back, fully readable by anyone who clones. That is the exact failure that
forced a history rewrite here once already.

**Every commit message on every ref**, not just the ones reachable from HEAD.

**Every annotated tag message.** Nothing was reading these at all.

The output never says which string matched, because this output is public.
"""

import os
import subprocess
import sys


def run(args: list[str]) -> str:
    return subprocess.run(args, capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout


def every_blob() -> list[tuple[str, str]]:
    """(sha, path) for every blob reachable from any ref, including deleted ones.

    Types come from one batch-check process. Asking `git cat-file -t` per object spawns
    one process per object, which on a few thousand objects turns a two second check
    into minutes, and a check nobody is willing to wait for gets removed.
    """
    candidates = []
    for line in run(["git", "rev-list", "--objects", "--all"]).splitlines():
        parts = line.split(" ", 1)
        if len(parts) == 2:  # a commit or a tag has no path and is skipped here
            candidates.append((parts[0], parts[1]))
    if not candidates:
        return []

    stdin = "\n".join(sha for sha, _ in candidates) + "\n"
    out = subprocess.run(["git", "cat-file", "--batch-check"], input=stdin.encode(),
                         capture_output=True).stdout.decode("utf-8", "replace")
    kinds = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            kinds[parts[0]] = parts[1]
    return [(sha, path) for sha, path in candidates if kinds.get(sha) == "blob"]


def blob_texts(blobs: list[tuple[str, str]]) -> dict[str, str]:
    """Read every blob in one batch. One process, not one per object."""
    if not blobs:
        return {}
    stdin = "\n".join(sha for sha, _ in blobs) + "\n"
    proc = subprocess.run(["git", "cat-file", "--batch"], input=stdin.encode(),
                          capture_output=True)
    out, texts, pos = proc.stdout, {}, 0
    while pos < len(out):
        nl = out.find(b"\n", pos)
        if nl == -1:
            break
        header = out[pos:nl].decode("utf-8", "replace").split()
        if len(header) < 3:
            break
        sha, size = header[0], int(header[2])
        body = out[nl + 1: nl + 1 + size]
        texts[sha] = body.decode("utf-8", "replace")
        pos = nl + 1 + size + 1  # trailing newline after the payload
    return texts


def main() -> int:
    names = [n.strip() for n in os.environ.get("FORBIDDEN_STRINGS", "").split(",") if n.strip()]
    if not names:
        print("FORBIDDEN_STRINGS is not set, so there is nothing to check against.")
        print("Set it if this repository must never mention certain names or paths.")
        return 0

    bad = set()

    blobs = every_blob()
    texts = blob_texts(blobs)
    for sha, path in blobs:
        text = texts.get(sha, "")
        for n in names:
            if n in text:
                bad.add(f"a forbidden string is in {path} (blob {sha[:8]}, "
                        f"reachable in history whether or not the file exists today)")
                break

    messages = run(["git", "log", "--all", "--format=%s%n%b"])
    for n in names:
        if n in messages:
            bad.add("a forbidden string is in a commit message")
            break

    tags = run(["git", "for-each-ref", "--format=%(refname:short)%0a%(contents)", "refs/tags"])
    for n in names:
        if n in tags:
            bad.add("a forbidden string is in an annotated tag message")
            break

    if bad:
        for b in sorted(bad):
            print(b)
        return 1

    print(f"clean: {len(blobs)} blobs across all of history, every commit message on "
          f"every ref, and every tag message, against {len(names)} forbidden strings")
    return 0


if __name__ == "__main__":
    sys.exit(main())

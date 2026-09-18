#!/usr/bin/env python3
"""
Conformance harness for harnessing/install-contract.md.

The contract is a document. A document nobody checks is instruction, not
enforcement -- the same failure this whole stack was written to close off,
now aimed at itself. This runs the sequence that actually proves it, against
every module in MODULES, against a fake Claude home each time:

  1. `--check` against a fresh fake home exits non-zero: nothing is installed.
  2. The installer runs for real and installs (exits zero).
  3. `--check` now exits zero.
  4. The installer runs a second time and reports no change on every item --
     idempotence *stated*, which is what the contract requires, not merely
     achieved silently.

Root-level because it reaches across modules, the same reason
scripts/check_no_leaks.py lives here rather than inside one module.

Never touches the real machine: every invocation below gets its own
tempfile.mkdtemp() as HOME/USERPROFILE and its own private working directory,
cleaned up in a `finally` so a failed assertion still cleans up. Runs the
same way locally as in CI.

The one trap worth naming explicitly: harnessing/install.py's doctrine-pointer
operation writes into whatever directory it is given, defaulting to the
process's cwd. Called carelessly -- cwd at the repo root, no --path -- it
would write CLAUDE.md/AGENTS.md into this repository and dirty the tree, here
and in CI. Every harnessing invocation below passes `--path <private temp
dir>` explicitly and also sets the subprocess `cwd` there, never at this
repository's root or this script's own directory. As a second, permanent
line of defense, this script snapshots this repo's own CLAUDE.md and
AGENTS.md before anything runs and compares again after everything finishes
-- if either changed, that is treated as fatal regardless of every other
result, on every run, not just once by hand (see `_repo_pointer_files_untouched`).

Usage:
  python scripts/check_install_contract.py
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parent.parent

# The files harnessing/install.py's doctrine-pointer operation would write if
# ever run with a cwd it wasn't given a --path for. Snapshotted before any
# subprocess runs, compared again at the very end.
GUARDED_FILES = [REPO_ROOT / "CLAUDE.md", REPO_ROOT / "AGENTS.md"]

STATUS_RE = re.compile(r"\[\s*([a-zA-Z]+)\s*\]")


@dataclass
class Module:
    name: str
    script: Path
    interpreter: str  # "python" or "bash" -- how this module's installer is run
    # Given this run's private working directory (never the repo root),
    # returns any extra argv the installer needs. harnessing needs --path;
    # devaing needs nothing.
    extra_args: Callable[[Path], list[str]] = field(default=lambda work_dir: [])


def _harnessing_extra_args(work_dir: Path) -> list[str]:
    # Never omit this: see the module docstring's trap paragraph.
    return ["--path", str(work_dir)]


# The declarative module list. Adding brainia once it is assessed against
# install-contract.md is one entry here, nothing else -- its absence right
# now is that assessment not having happened yet, not an error (the doctrine's
# own line: a module that is absent is information).
MODULES: list[Module] = [
    Module("harnessing", REPO_ROOT / "harnessing" / "install.py", "python", _harnessing_extra_args),
    Module("devaing", REPO_ROOT / "devaing" / "install.sh", "bash"),
]


def _interpreter_command(interpreter: str) -> list[str] | None:
    """None means unavailable on this machine -- the caller skips, not fails."""
    if interpreter == "python":
        return [sys.executable]
    if interpreter == "bash":
        bash = shutil.which("bash")
        return [bash] if bash else None
    raise ValueError(f"unknown interpreter {interpreter!r}")


def _snapshot(paths: list[Path]) -> dict[Path, bytes | None]:
    return {p: (p.read_bytes() if p.is_file() else None) for p in paths}


def _run(module: Module, args: list[str], env: dict, work_dir: Path) -> subprocess.CompletedProcess:
    interp = _interpreter_command(module.interpreter)
    cmd = interp + [str(module.script)] + args + module.extra_args(work_dir)
    return subprocess.run(cmd, env=env, cwd=str(work_dir), capture_output=True, text=True)


def _statuses_in(output: str) -> set[str]:
    return {m.group(1) for m in STATUS_RE.finditer(output)}


def _describe(r: subprocess.CompletedProcess) -> str:
    return f"    stdout:\n{r.stdout}\n    stderr:\n{r.stderr}"


def check_module(module: Module) -> list[str]:
    """Returns failure descriptions; empty means the module is fully conformant."""
    interp_cmd = _interpreter_command(module.interpreter)
    if interp_cmd is None:
        print(f"  [skipped ] {module.name}: interpreter '{module.interpreter}' not found on "
              f"this machine -- not assessed, not failed")
        return []

    if not module.script.is_file():
        return [f"{module.name}: installer script not found at {module.script}"]

    failures: list[str] = []
    fake_home = Path(tempfile.mkdtemp(prefix=f"conform_home_{module.name}_"))
    fake_work = Path(tempfile.mkdtemp(prefix=f"conform_work_{module.name}_"))
    try:
        (fake_home / ".claude").mkdir(parents=True)
        env = dict(os.environ)
        env["HOME"] = str(fake_home)
        env["USERPROFILE"] = str(fake_home)

        # 1. --check on a fresh fake home: nothing installed, must be non-zero.
        r = _run(module, ["--check"], env, fake_work)
        print(f"  [1/4] {module.name} --check (fresh): exit {r.returncode}")
        if r.returncode == 0:
            failures.append(f"{module.name}: step 1 -- `--check` on a fresh install exited 0, "
                             f"expected non-zero (nothing is installed yet).\n{_describe(r)}")

        # 2. Install for real.
        r = _run(module, [], env, fake_work)
        print(f"  [2/4] {module.name} install: exit {r.returncode}")
        if r.returncode != 0:
            failures.append(f"{module.name}: step 2 -- the install run exited {r.returncode}, "
                             f"expected 0.\n{_describe(r)}")

        # 3. --check after install: must now be zero.
        r = _run(module, ["--check"], env, fake_work)
        print(f"  [3/4] {module.name} --check (installed): exit {r.returncode}")
        if r.returncode != 0:
            failures.append(f"{module.name}: step 3 -- `--check` after a real install exited "
                             f"{r.returncode}, expected 0.\n{_describe(r)}")

        # 4. Install again: idempotence has to be *stated*, not just true. Every
        # reported item must say "ok" -- anything else means a rerun still
        # thinks it has work to do, which is the contract's idempotence
        # requirement failing even if the end state happens to be correct.
        r = _run(module, [], env, fake_work)
        print(f"  [4/4] {module.name} second install: exit {r.returncode}")
        if r.returncode != 0:
            failures.append(f"{module.name}: step 4 -- the second install run exited "
                             f"{r.returncode}, expected 0.\n{_describe(r)}")
        else:
            seen = _statuses_in(r.stdout)
            changed = seen - {"ok"}
            if changed:
                failures.append(
                    f"{module.name}: step 4 -- a second install run reported status(es) "
                    f"{sorted(changed)} instead of only 'ok'. Idempotence is not being stated: "
                    f"a rerun still claims to have work to do.\n{_describe(r)}"
                )
    finally:
        shutil.rmtree(fake_home, ignore_errors=True)
        shutil.rmtree(fake_work, ignore_errors=True)

    return failures


def main() -> int:
    print("Conformance harness for harnessing/install-contract.md")
    print(f"Modules assessed: {', '.join(m.name for m in MODULES)}")
    print("(brainia joins this list once it is assessed against the contract; its absence "
          "here is that, not an error)")
    print("bash-based modules assume `bash` is on PATH (Git Bash on Windows, native on "
          "Linux/macOS) -- a machine without it skips those modules rather than failing.\n")

    before = _snapshot(GUARDED_FILES)

    all_failures: list[str] = []
    for module in MODULES:
        print(f"=== {module.name} ===")
        failures = check_module(module)
        if failures:
            all_failures.extend(failures)
        else:
            print(f"  {module.name}: conforms to install-contract.md\n")

    after = _snapshot(GUARDED_FILES)
    if before != after:
        all_failures.append(
            "HARNESS FAULT: this repository's own CLAUDE.md/AGENTS.md changed during this run. "
            "An installer wrote into the real repo instead of a private temp directory. This "
            "is fatal on its own, regardless of every other result above."
        )

    if all_failures:
        print("conformance failures:")
        for f in all_failures:
            print(f"  - {f}")
        return 1

    print("all assessed modules conform to install-contract.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

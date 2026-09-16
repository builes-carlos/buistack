# The install contract

What any `buistack` module's install step has to guarantee, so that "what of mine is
out of date" has one honest answer instead of three different shapes of guess. This is
a spec to check an installer against, not an essay about installers.

Scope: **installing this repo's own tooling onto a machine** (skills, hooks, config
blocks). It does not cover syncing a module's own tracked files from an external
upstream template — that is a different verb, and a module that does both must not let
one wear the other's name (see brainia, out of scope this document, below).

`harnessing/install.py` is the reference implementation. Every requirement below is
drawn from what it already does, not invented for this document.

## Requirements

- **Idempotent.** Running it twice changes nothing the second time. It reports that
  nothing changed rather than silently doing nothing.

- **A `--check` mode that writes nothing, and exits non-zero while anything is
  incomplete.** This is what makes it usable from a gate or a session-start hook
  instead of only from a human's memory.

- **No network.** Installing onto a machine is a local operation: this clone's files
  onto this machine's config. Anything that fetches from a remote — an upstream
  template, a package registry — is a different verb and must not share the command,
  the flag, or the name with this one.

- **Non-interactive.** Runnable from a hook or a CI gate with nobody at the keyboard:
  no prompts, no confirmation gates, no reading from stdin for a decision.

- **Per-item reporting, with a state vocabulary, never a single pass/fail.** One line
  per thing installed, naming what state that thing is in. Four states apply to
  anything installed by any mechanism:

  | State | Means |
  |---|---|
  | absent | not installed at all |
  | current | installed and correct (reported `ok`) |
  | stale | installed, but content or registration has drifted from the source |
  | obstructed | something not owned by this installer is in the way; never touched |

  Two more states are specific to a **link-based** install (installing a skill as a
  symlink or junction into the clone, rather than writing a copy of it) and do not
  apply to anything written by value, such as a hook script or a config block:

  | State | Means |
  |---|---|
  | linked | a specialization of `current` that cannot go stale, because the installed thing *is* the source |
  | dangling | a specialization of `stale`: the pointer exists but resolves to nothing, because the source moved or was deleted |

  A copy-based installer reports the first four and never the last two. A link-based
  one reports all six, and `dangling` is the state that has no analogue in a
  copy-based world — a copy left behind by a deleted source is still a working copy;
  a dangling link is not.

- **Never destroys without confirming what it is replacing exists elsewhere, and
  never touches anything it does not own.** Concretely: verify the source is present
  and resolves *before* removing what is currently installed, and never remove
  something that is not recognizably this installer's own (an unrelated file where a
  managed directory or link is expected is `obstructed`, not a target). If the source
  is missing, leave whatever is installed exactly as it is — a stale or dangling
  install beats no install.

- **Says what it changed, every time.** Every write is named in the output: what was
  installed, updated, or repaired, and where. A silent installer is how drift hides,
  which is the entire premise this contract exists to close off.

- **Declares what it depends on, and reports rather than fails when a dependency is
  absent.** A module that is absent is information, not an error (already the rule
  for the modules themselves; an installer follows the same rule for its own
  dependencies). If a sibling piece is missing — a doctrine file an injector would
  read, a script a hook would call — the installer states the consequence (which
  pointer will not resolve, which feature stays inert) and completes rather than
  aborting.

## What this contract does not require

**No implementation language is mandated.** Bash, Python, anything else that can
satisfy every requirement above satisfies the contract. This document is about
observable behavior, not about which interpreter runs it.

**A separate observation, not a rule, because this is where the stack actually runs:**
bash pays a real cost on Windows that Python does not. A bash installer either requires
Git Bash or WSL to be present — an assumption this stack cannot make silently, since
nothing else in it requires either — or it has to be reimplemented in something that
ships with Windows. Python 3, by contrast, is already the one interpreter every
requirement above (`--check`, no network, idempotence) is cheap to implement in, and it
is what `harnessing/install.py` already uses. This is a cost to weigh, not a rule this
contract enforces: a bash installer that is never run outside Linux/macOS use is not in
violation of anything above.

## Status of each module against this contract

- **harnessing** (`install.py`): meets it. Reference implementation.
- **devaing** (`install.sh`): meets every requirement above except one. It reports per
  item in the same state vocabulary, answers `--check` without writing, names only what
  it actually changed, refuses to write over anything it does not own, and says so when
  `~/.claude` is absent instead of failing. What it does not do is **link**: it still
  copies each skill, so a devaing install goes stale the moment the repository moves
  ahead, which is the failure harnessing removed for its own skills by linking instead.
  Whether devaing should link too is a decision about that module, deliberately not
  taken here.
- **brainia**: not assessed. It carries two scripts wearing similar names for two
  different verbs (`brainia-update.sh` fetches from an external upstream;
  `global-hooks/install.py` installs one hook onto the machine), and untangling which
  of them this contract even applies to is its own decision, not a detail of whichever
  slice happens to touch it first.

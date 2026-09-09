---
name: harnessing-audit
description: Audit structure and installation against harnessing's doctrine. Never audits code. Checks that .md files sit at the right layer, that no layer duplicates another, that the instance is where the convention says, and that the doctrine is actually being injected. Use when the user wants to check drift in their agent-facing docs, verify a harnessing install, or asks whether their structure has rotted.
---

# harnessing-audit

Audits **structure and installation**, never code. Runs the same way over a
single software repo, a vault, or the whole personal-root container: the
checks below are about where things live and whether the install is real,
not about what a codebase does.

Auditing code artifacts against software doctrine (spec claims without a
citation, acceptance criteria without EARS, a feature doc out of sync with
its code) is devaing's job, inside `devaing-director`'s health audit. This
skill does not duplicate that.

## Why this exists

harnessing's own construction found every one of the checks below by hand,
before this skill existed: doctrine that contradicted the module it was
supposed to govern, a rule written three times across three files, a skill
duplicated between a plugin and a global install, a stale copy of a doc that
had already been superseded, and a rule that had to clarify in its own text
which of its two copies wins. Structure drifts again the moment nobody is
watching for it, so the value of finding it once only survives if the check
lives in a skill instead of in a memory of the session that found it.

## Checks

Run each of the following. Report every hit with the file paths involved,
not a summary count.

### C1: Layer placement

For each `.md` file this audit can reach, determine what layer it is
actually written at (personal root, front, workspace, or project, per
`structure/README.md`) and what its content claims to be. Flag a file whose
content belongs at a different layer than the one it lives at, for example
a workspace-wide gotcha sitting inside one project's `AGENTS.md`, or method
that belongs in harnessing's doctrine written inline in a project file.

### C2: Upward duplication

For every pair of layers in a parent-child relationship, grep for passages
that appear in both. This is the check most likely to fire: a layer
repeating the one above it is the single most common way this structure
rots. Any hit is worth reporting even if the two copies still agree today,
since a duplicate that agrees today is a contradiction waiting for one side
to be edited without the other.

### C3: Stale derivation

For any upper-layer doc that summarizes or depends on a fact owned by a
feature-level doc (a `docs/features/<area>.md`, a project's `CONTEXT.md`),
grep the upper doc for the old claim whenever the underlying fact has
visibly changed (a different value now written at the feature layer, a
section marked superseded). Flag the upper doc's stale copy.

### C4: Cross-layer rule duplication

Beyond the parent-child check in C2, look for the same rule stated in two
layers that are not in a direct parent-child relationship (two sibling
projects, a front and an unrelated project). A rule stated more than once
anywhere in reach of the same agent is a duplication regardless of which
two layers hold the copies.

### C5: Instance placement and naming

Locate every framework instance reachable from the audit root (a
`harnessing-*`, `brainia-*`, or similar folder). For each: confirm it sits
at the layer that matches its own scope (per the convention in
`structure/README.md`'s "Where instances live"), and confirm its name
follows `<framework>-<user>`, framework first. Flag a mismatched order (a
`<user>-<framework>` name) or an instance sitting at the wrong depth (for
example, one framework's instance nested inside another framework's
instance).

### C6: Hook registration and injection

Claude Code only. Check `~/.claude/settings.json` for a `SessionStart` hook
entry pointing at `harnessing_inject_doctrine.py`, confirm the script exists
at the path the entry names, and confirm `doctrine/condensed.md` exists at
the path the script would read. A registered hook pointing at a missing
script or a missing doctrine file is worse than no hook: it looks installed
and silently injects nothing.

```bash
python <this clone>/install.py --check
```

Cross-check its output against what this step found by hand; a mismatch
between the two means the check above or `install.py` itself has drifted
from the other.

### C7: Durable facts stuck in ephemeral storage

Look for signs that something durable (a gotcha, a decision, a recurring
trap) exists only in an agent's own auto-memory or in a session transcript,
never written to a versioned `.md` at the layer that reaches or synced to
the vault. This is hard to check directly (auto-memory is not on disk in a
form this skill can read across agents), so check the proxy: ask the user
whether anything they consider "settled" only lives in a conversation they
remember, and if so, write it to the layer that reaches before closing the
audit.

### C8: Stage ownership

Walk `harnessing/README.md`'s stage-to-owner map. For each stage, confirm
exactly one owner is installed and active for it, given which modules are
present on this machine. Flag a stage with zero owners (a gap: something in
the loop nobody currently handles) and a stage with two owners (a
collision: two skills both trying to run at the same point, which is how a
stage ends up run twice or run inconsistently depending on which skill fires
first).

## Report format

```
harnessing-audit: <target>

C1  Layer placement       <N hits, or clean>
C2  Upward duplication    <N hits, or clean>
C3  Stale derivation      <N hits, or clean>
C4  Cross-layer dup       <N hits, or clean>
C5  Instance placement    <N hits, or clean>
C6  Hook registration     <ok | broken: reason>
C7  Durable-in-ephemeral  <N flagged, or clean>
C8  Stage ownership       <N gaps, N collisions, or clean>

<for each hit: file path(s), one line describing what is wrong>
```

Do not propose fixes inline for every hit; list them. A structural fix
(moving a rule to a different layer, deduplicating a passage) is itself
enough of a change that it deserves its own confirmation before an agent
starts editing files across layers.

# harnessing

The discipline of working with agents, independent of what you build with them.

Every session with an AI agent pays for a dispatch decision: one agent or three,
a fresh one or a reused one, a subagent or the lead itself. Get that wrong often
enough and the waste shows up as a token bill, not as a bug. harnessing is the
part of the stack that answers those questions before any code, any spec, or
any vault entry exists. It governs how work gets handed to an agent. It does
not care whether that work is a software feature or a personal errand.

## What it governs

- **The doctrine.** How a go is scoped, when a fresh agent is worth its
  read-the-world cost, when review has to happen in a clean context, what
  "verify the tree, not the report" means in practice. Lives in `doctrine/`,
  always loaded, never invoked.
- **The stage-to-owner map.** Which framework owns which point in the life of
  a project, so two modules never compete for the same stage and none is left
  unowned. See below.
- **The `.md` hierarchy.** The layers a repo or a machine can carry
  (`structure/`), what each one is allowed to hold, and what it must never
  repeat from the layer above.
- **The module contract.** devaing and brainia implement this doctrine in
  their own domain. harnessing does not require either to function, and
  neither requires harnessing.

## What it does not govern

Building software is devaing's domain. Running a personal vault is brainia's.
harnessing carries the vocabulary both borrow (see `doctrine/universal.md` for
the shared agent roles) and the mechanism that gets any of them off the
ground, nothing about how a codebase or a vault should be organized inside
itself.

## Install, from the clone

```bash
git clone https://github.com/builes-carlos/buistack.git
cd buistack/harnessing
python install.py --check     # see what's missing, writes nothing
python install.py             # bootstrap: skills + doctrine pointer + hook
```

Bare `install.py` is the idempotent primitive: it detects which agents are on
the machine (`~/.claude`, `~/.codex`, `~/.gemini`) and writes only to those,
never overwrites a file it does not already own a marked block in, and
prints what it wrote, what it skipped, and why.

Most people should not call it directly. Run the setup skill instead, once
the bootstrap above has put it on the machine:

```
/harnessing-init
```

`harnessing-init` asks three questions and one confirmation, detects
everything else (see `skills/harnessing-init/SKILL.md`), and calls
`install.py` with the answers. `install.py` alone does not know where your
instance goes or what your profile says; the skill is what turns detection
into a decision.

To check the install later, or audit a repo that has drifted:

```
/harnessing-audit
```

## The contract between modules

**Modules suggest each other. They never require each other.** devaing's
`STRATEGY.md` lists harnessing as its governing doctrine, and brainia's
`fronts/code.md` points at devaing for the software front, and neither
import breaks if the pointed-at module is missing. An absent module is
information your agent reports, never an error that halts a skill.

**Each one is fully effective alone.** Someone who installs only harnessing
gets the complete discipline of dispatch: the roles, the context-compression
rules, the `.md` hierarchy. They lose nothing by not also building software
through devaing or running a vault through brainia. The same holds in
reverse: devaing without harnessing still ships software, just without the
shared vocabulary for agent roles, and it falls back to an inline description
of each pattern instead of pointing at harnessing's doctrine.

**Detection replaces dependency.** Any skill that would benefit from another
module checks for it on disk (a directory, a marker file, a skill already
installed under `~/.claude/skills/`) and adapts. It never fails a run because
the other module is absent, and it never installs the other module on the
user's behalf: that decision belongs to the user.

## The stage-to-owner map

`office-hours` is a pre-gate, not a stage in the loop: it runs once, before a
project exists, and nothing downstream depends on it. It lives here rather
than inside brainia's business front because it gates the whole stack, not
just brainia's domain, and because someone who adopts harnessing plus devaing
without brainia should still see it.

| Stage | Owner | Provenance |
|---|---|---|
| Pre-gate: evaluate a business idea | `office-hours` | own file, gstack provenance, lives in harnessing |
| Domain discovery | `grill-me`, invoked by `devaing-phase-def` | Pocock |
| Phase, epics, prototype, backlog | `devaing-phase-def` (uses `prototype`, `triage`) | own |
| In-flight scope adjustment | `devaing-phase-revise` | own |
| Slice specification | the lead, software doctrine lives in devaing | own |
| Slice construction | `devaing-work`, Backlog or Direct lane | own |
| Testing | devaing's three test layers, `Testarossa` | own |
| Adversarial review | `ce-adversarial-reviewer`, `ce-data-integrity-guardian`, invoked by `devaing-work` | Compound Engineering |
| Debugging a non-obvious cause | `diagnose`, invoked by `devaing-bug` | Pocock |
| Architecture audit at phase close | `improve-codebase-architecture`, invoked by `devaing-work` | Pocock |
| Path to production | `devaing-ship` | own |
| State and next step | `devaing-director` | own |
| Durable memory | `front-sync` toward the vault | brainia |
| How anything gets dispatched to an agent | harnessing doctrine, always loaded | own |

Utilities without a stage, and that is fine because they never compete for
one: `write-a-skill`, `find-skills`, `caveman`, `zoom-out`.

## Structure of this folder

```
harnessing/
  README.md          this file
  doctrine/           the doctrine itself: universal.md, condensed.md, SOURCES.md
  install.py          idempotent installer, --check mode
  hooks/              SessionStart hook script installed into ~/.claude/hooks/
  structure/          the .md hierarchy: layer contract and templates
  profile/            _template.md, so an instance can declare itself
  skills/
    harnessing-init/   setup: three questions, one confirmation, everything else detected
    harnessing-audit/  audits structure and installation, never code
    office-hours/      pre-gate: is this idea worth building
```

## Versioning

Tagged with its own prefix, `harnessing-v…`, independent of `devaing-v…` and
`brainia-v…`. A change to the doctrine must not bump either module's version
number.

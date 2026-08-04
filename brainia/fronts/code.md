---
front_id: code
display_name: Code
aliases: [Code]
sibling: Code/
writes_to: [vault/04-projects/]
methodology: devaing
reads_back: [CONTEXT.md, CHECKPOINTS.md]
skills: []
profiles: [engineer, engineering-lead]
integrations: []
---

# Front Pack: Code

**Execution only.** The Code front covers building and shipping software, plus the discovery
that directly feeds a build (specs, prototypes, architecture). It does not own the venture the
software belongs to: strategy, market intel, ownership/legal, co-founders, and the user's own
pay live in `strategy`, `biz`, `people`, `finances`, etc. A single venture routinely spans
several fronts at once — Code is just the slice where code gets written.

## Methodology: devaing

devaing is an external framework for building products with AI via GitHub-issue-sized,
self-contained units of work.

- **Source:** <https://github.com/builes-carlos/devaing> (public). This is the canonical
  reference. Do not point at a local path as if it were the source; a path only exists on the
  machine that already has it.
- **Install:**
  ```bash
  git clone https://github.com/builes-carlos/devaing.git
  cd devaing && bash install.sh
  ```
  `install.sh` copies each `skills/devaing-*/` folder into `~/.claude/skills/`, so devaing
  installs itself machine-wide and is not vendored into any brain.
- **Detection:** presence of `devaing-*` directories in `~/.claude/skills/`.
- **Local convenience only:** if devaing is already cloned as a project inside this front
  (`Code/devaing` in the author's own container), use it from there. That path is not part of
  the contract and its absence means nothing is wrong.

### Entry points, in order

1. `/devaing-director` — start here. Project state, health audit (CHECKPOINTS C1-C5), and a
   next-step recommendation.
2. `/devaing-init` — bootstrap a new devaing project.
3. `/devaing-phase-def` — define a phase: discovery, epics, prototype, issue generation.
4. `/devaing-work` — implement issues on epic branches.
5. `/devaing-phase-revise` — adjust scope mid-phase.
6. `/devaing-ship` — deploy to prod.
7. `/devaing-bug` — turn a bug report into a structured issue.
8. `/devaing-help` — framework reference.

### NON-OWNERSHIP — read this before touching a code project

**Brainia does not plan, build, review, or ship code. It hands off to devaing and stops.**
Brainia contains no development tooling and never will — no build systems, no test runners, no
deploy scripts, no issue-tracker clients of its own. When a code task comes up, the correct
Brainia action is to point at the devaing entry point above, not to attempt the work itself.

## reads_back: CONTEXT.md and CHECKPOINTS.md

devaing already maintains, per project, `CONTEXT.md` (domain glossary, architecture, key
constraints, known limitations, phases table) and `CHECKPOINTS.md` (objective health criteria).
Brainia reads these two artifacts into `vault/04-projects/<project>/` — this is how execution
feeds the brain without the brain ever owning execution: devaing does the building and keeps
its own living truth, Brainia only distills what devaing already wrote down.

## Profiles

`engineer` and `engineering-lead` — see `fronts/code/profiles/`.

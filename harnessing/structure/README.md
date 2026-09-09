# The `.md` hierarchy

Doctrine without the structure it lands on is a list of maxims. harnessing
declares the layer model and ships the templates. Each repo, vault, or
machine implements it by filling in the templates that apply, and skipping
the ones that don't.

## Declared by role, not by a fixed tree

The tree on any one machine is not universal: how many layers exist depends
on how the human organizes their life and work, an instance's shape differs
by framework, and names are per user. What is fixed is what each layer is
for. All layers below the project layer are optional. Project is not: it
always exists, because it is where an agent actually reads and writes code.

| Layer | Exists when | Holds | Never holds |
|---|---|---|---|
| Personal root | More than one front is in play | A pointer to the fronts, nothing else | Method: that already lives in harnessing |
| Front | A domain of life or work is managed apart from the others | Which module it delegates execution to, and how to detect that module | Rules that belong to one specific project |
| Workspace | Several projects share a machine | Machine and environment: caches, the automation browser, per-repo accounts, worktrees | Doctrine, and anything that would not travel to another machine |
| Project | Always | `CONTEXT.md` (domain, architecture, decisions, live constraints), `AGENTS.md` (commands, where things live, project-specific gotchas), `CLAUDE.md` as a shell that points at `AGENTS.md`, `CLAUDE.local.md` for anything that cannot be committed, `docs/features/<area>.md` | Method, and any gotcha that would bite in any project on the same stack |

Templates for each layer live in `templates/`: `templates/root-personal.md`,
`templates/front.md`, `templates/workspace.md`, and `templates/project/` for
the four project-level files.

## Three rules that make it work

These are the rules that break in practice, which is exactly why they are
worth stating rather than assuming.

- **A layer is chosen by where it reaches, never by where it is convenient to
  write.** This is the root rule. Every drift this framework has had to
  correct in its own construction was a case of violating it: a rule that
  belongs to the whole stack written into one module because that module
  already had an installer, a check that belongs to one repo written into
  the umbrella because the umbrella had a lint step running.
- **A layer never repeats the one above it.** A `CLAUDE.md` that copies out
  the method is guaranteed to drift: it is a shell and a pointer, nothing
  more. A passage duplicated across two layers will eventually contradict
  itself, and the layer above drifts silently because nobody notices the
  copy went stale.
- **A gotcha that would bite in any project on the same stack is not a
  project's gotcha.** It belongs at whichever layer actually reaches every
  project it would bite. Admission filter, all three have to hold: it is not
  discoverable by reading the code, it generalizes past a single component,
  and the obvious approach is wrong.

## The loading mechanics

This is verifiable, and as of this writing it is not published anywhere else
in the stack.

- **`CLAUDE.md` and `AGENTS.md` load the file at the current directory plus
  every parent directory above it.** A rule placed at the workspace layer
  reaches every project under it automatically. A rule placed inside one
  project reaches only that project.
- **Skills load per subtree.** A skill only fires when the working directory
  is somewhere inside the tree the skill was installed under (a project
  clone, a vault). A skill installed globally under `~/.claude/skills/` fires
  everywhere; one copied into a project's `.claude/skills/` fires only
  inside that project.
- **An agent's own auto-memory is indexed by the literal path where the
  session was opened, and it does not cascade.** Opening a session one level
  deeper than where a memory was written will not find it, and renaming the
  folder a memory is indexed under orphans it silently, with no warning from
  the tool. This is the reason almost nothing durable can live only in
  auto-memory: it has to be written to a versioned `.md` at the layer that
  reaches, or to the vault through `front-sync`, or it is gone the moment a
  folder moves.

## Where instances live

harnessing declares this convention; it is not enforced by any script,
because enforcing it would mean owning paths that belong to whichever module
is scaffolding at the time.

- **Framework clones live together, outside the project tree.** A framework
  is not a product being built, it is a tool the human installed, so it does
  not belong next to client or personal projects. Anything from a third
  party that is read for reference and never run belongs in a `_ref/`
  folder, underscored so it sorts to the top of a listing and reads at a
  glance as not-a-project.
- **Each instance lives at the layer that matches its own scope**, not at a
  fixed depth. A framework with one instance per machine (its scope is the
  whole human, or the whole workspace) lives at the personal-root or
  workspace layer. A framework with many instances (its scope is one
  project at a time) has its instance live inside each project.
- **An instance is named `<framework>-<user>`, framework first.** The
  framework name goes first because it is what gets read first and what
  keeps instances of different frameworks sorted together in any listing.
  The user's name goes second because instances of the same framework
  belonging to different people is the case that actually needs
  disambiguating, and the framework name is what a stranger reading the
  listing needs to recognize before anything else.

## Where an `office-hours` verdict lands

`office-hours` runs before a project exists, so it cannot write into a
project's own docs; there is no project yet to write into. Its verdict
lands in one of two places, so a "not yet" verdict always has a home instead
of evaporating with the conversation that produced it:

- **If a vault is installed** (brainia present), the verdict goes to the
  vault through the business front, alongside every other durable artifact
  that front produces.
- **If no vault is installed**, the verdict goes to
  `<harnessing instance>/reviews/office-hours-<date>-<slug>.md`, inside
  whichever harnessing instance the machine has. This keeps harnessing
  usable standalone: a module that only fires when another module happens
  to be present would break the suggest-never-require contract.

## Frontier with the modules that scaffold

brainia already scaffolds the container and the fronts. devaing already
scaffolds a project (`CONTEXT.md`, `CHECKPOINTS.md`, `.devaing/`). If
harnessing also wrote those files, two scaffolders would fight over the same
path on every install.

So: **harnessing declares the contract for each layer and ships the
templates in this folder. Whoever is scaffolding uses them if they are
present.** harnessing's own scaffold, run by `harnessing-init`, only fills
gaps at layers no other module owns, and it never overwrites a file that
already exists, templated or not: it reports and moves on.

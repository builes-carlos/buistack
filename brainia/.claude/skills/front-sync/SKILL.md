---
name: front-sync
description: Distill the artifacts an active front declares in reads_back into vault notes, and mine mines_durable artifacts for durable findings routed by how far they generalize, so work done outside the brain feeds back into it
front: all
integrations: []
---

# Front Sync Skill

## Purpose

Close the loop between execution and the brain. Each front pack declares `reads_back`: the
artifacts that the front's own methodology already maintains in its sibling folder. This skill
reads those artifacts and distills them into vault notes at the front's `writes_to` location.
That is state: where things stand right now.

A front pack can also declare `mines_durable`: artifacts where gotchas, stack traps, and
litigated decisions tend to land instead. This skill mines those separately and routes each
finding by scope (project, stack, or universal) instead of distilling them as state. State
answers "where do things stand"; durable knowledge answers "what's true regardless of when you
ask." Both close the same loop; neither substitutes for the other.

This is the mechanism that lets Brainia learn what happened downstream **without owning any of the work**. The software front is the first case: devaing maintains each project's `CONTEXT.md` and `CHECKPOINTS.md`, and this skill distills them. Nothing here is specific to devaing. Any front that declares `reads_back` syncs the same way, and any front that declares `mines_durable` mines the same way.

## When to Invoke

- User says "sync my fronts", "front sync", "pull in my project state", "what changed in my projects"
- After a work session in a front whose methodology wrote artifacts (a phase shipped, a checkpoint changed)
- Before any question that depends on current project or front state, when the last sync is stale
- As a step inside `weekly-checkin` or `comprehensive-analysis` when front state is out of date

## The rule this skill must never break

> **The vault is a reference layer, never a storage drawer.**

Never copy a source artifact into the vault. Never move working files in. What lands in the vault is a **distilled note that cites the source and points back at it**. If a sibling artifact is large, the note gets shorter, not the vault fatter. See the HARD RULE in `CLAUDE.md`.

## Agent Mode Awareness

**Check `agent_mode` in `vault/00-inbox/MY-PROFILE.md` frontmatter:**
- If `agent_mode: team` — delegate the reading to a `worker-file-ops` or `worker-data-collector` sub-agent (Sonnet), one per front. Each worker writes its extraction to `/tmp/front-sync-<front_id>.md` and returns only a status plus the path. The lead session reads those files and does the distillation and judgment.
- If `agent_mode: solo` (default) — read and distill directly.

Reading many artifacts is data collection, so it belongs to a Sonnet worker per the Model Routing table. Deciding what is worth keeping is judgment, so it stays with the lead. This applies doubly to the durable-knowledge pass: a worker may read `mines_durable` artifacts and list candidate claims, but the admission filter, the scope proposal, and the dedup check are judgment calls the lead makes itself, never delegated.

## Pre-Flight Check

1. **Resolve active fronts.** Read `active_fronts` from `vault/00-inbox/MY-PROFILE.md` frontmatter. If it is absent, tell the user to run `/onboarding` and stop.
2. **Scope.** If the user named a front, sync only that one. Otherwise sync every active front that declares a non-empty `reads_back` or a non-empty `mines_durable`: a front can have either, both, or neither.
3. **Get the real timestamp.** Run `date '+%Y-%m-%d %H:%M'` via Bash. Never guess or fabricate a date; it is the basis of every staleness judgment in the output.

## Part A: State Sync

Distills `reads_back` artifacts into a project's current-state note. Unchanged from before durable knowledge existed as a separate pass.

### 1. Read the contract, not the assumption

For each front in scope, read `fronts/<front_id>.md` and take from its frontmatter:

- `sibling` — the container folder to read from
- `reads_back` — the artifact filenames to look for
- `writes_to` — the vault path the distilled note belongs in

`mines_durable` is a separate list read the same way, for Part B below. A front may declare one, the other, both, or neither; each list is located and processed independently.

**Never hardcode a filename.** If a pack declares `reads_back: [STATUS.md]`, that is what gets read. The pack is the contract.

### 2. Locate the artifacts

Most fronts hold several units of work (the software front holds one per project), so expect **one set of artifacts per unit**, not one per front.

**A unit is the directory that contains the declared artifacts, not the top-level folder.** This matters and getting it wrong loses whole projects: in a real container the artifacts sit at `Code/<project>/CONTEXT.md` but also at `Code/<project>/<app>/CONTEXT.md`, `Code/<client>/<project>/CONTEXT.md` and `Code/<client>/<project>/CONTEXT.md`. A top-level-only scan silently misses every nested one.

So: search the sibling folder recursively to a **bounded depth of 3**, skipping vendored and build directories (`node_modules`, `.git`, `dist`, `build`, `.next`, `target`, `venv`, `__pycache__`). Any directory holding at least one declared artifact is a unit.

**Skip linked git worktrees.** A parallel-work worktree carries a full copy of the artifacts, so a naive scan turns one project into a dozen units whose notes all describe the same thing and go stale the moment the worktree is removed. In one real container, 8 of 18 resolved units were per-issue worktrees of a single project.

The detection is exact and cheap: in a **linked worktree** `.git` is a *file* whose first bytes are `gitdir:`, while in a **primary checkout** `.git` is a *directory*. Skip the former, keep the latter. Do not try to guess from the folder name; naming conventions for worktree parents vary per person and per machine.

If a unit's only copy of the artifacts lives in a worktree and the primary checkout has none, report it as a unit with a note saying so rather than dropping it silently.

**Flag unversioned units instead of trusting them.** Worktree detection catches live worktrees but not dead ones. In the same real container, one unit had no `.git` at all: an abandoned copy of another project's tree, left behind days earlier when a worktree was removed without its directory. By inspection it is indistinguishable from a real project, and syncing it produces a note that duplicates the real one and never updates again.

So record per unit whether it is a git repository, and for a front whose work is normally versioned, **list unversioned units separately and sync them only if the user confirms**. Do not skip them automatically: a legitimate project may simply not use git. Do not delete anything either; a stray directory is the user's to resolve, and it may sit in a folder you have no authority over.

Derive the unit slug from the path relative to the sibling, collapsing to the top-level folder name when the artifacts sit directly in it (`myproject`) and keeping the distinguishing segment when nested (`myproject-webapp`). If two units would collapse to the same slug, keep the full relative path so nothing overwrites anything.

Record, for each unit found:
- which declared artifacts exist
- which are missing
- the modification date of each
- its path relative to the sibling, for the citation

A missing artifact is information, not an error. It usually means that unit has not been set up with the front's methodology yet. Report it and move on. Some units will have `CONTEXT.md` but not `CHECKPOINTS.md`, which simply means they were not initialized by the methodology that creates it.

### 3. Distill, do not transcribe

For each unit, write or refresh a note at `<writes_to>/<unit-slug>/` capturing only what a future question would need:

- **Current state** — where the work stands right now, per the artifact
- **What it is** — one or two sentences, from the artifact's own framing
- **Constraints and known limitations** — the parts that would make someone give bad advice if they did not know them
- **Open risks** — anything the artifact flags as unresolved
- **What changed since the last sync** — see step 4

Skip anything the artifact holds that is better read at the source: full glossaries, complete architecture descriptions, file inventories. The note links to the source instead.

Every factual claim carries a citation in the repo's format:

`[Source: ../../<Sibling>/<unit>/<FILE>.md | YYYY-MM-DD | confidence: high]`

Confidence is `high` when the claim is quoted from the artifact, `medium` when inferred across artifacts, `low` when the artifact is ambiguous. Never write a claim with no source.

### 4. Report what changed, including what stopped being true

If a note already exists for this unit, **diff the meaning, not the text**. This is the half that makes the brain correct itself rather than only grow:

- **New** — facts present now and absent before
- **Changed** — facts whose value moved (a phase advanced, a constraint was lifted)
- **Invalidated** — claims the vault asserted that the artifact now contradicts. **Correct them in place and say so.** A stale claim left standing is worse than a missing one.
- **Stale** — the source artifact has not moved since the previous sync, so nothing here is fresher than that date

Write the changes into the note's own history section, append-only, and surface them in the run summary. Never rewrite history; only the distilled current-state section gets updated.

### 5. Summarize for the human

Report per front and per unit: synced, unchanged, missing artifacts, and every invalidated claim. Lead with the invalidations, because those are the ones that were actively misleading. If Part B also ran, fold its summary (step 8 below) into the same report rather than issuing two separate ones. The human asked for one sync, not two.

## Part B: Durable Knowledge

State sync returns what's happening. This pass returns what's true regardless of when you ask:
gotchas, stack traps, litigated decisions, findings that would make someone waste a day
rediscovering something already known. It runs for every front in scope that declares a
non-empty `mines_durable`, independently of whether that front also has `reads_back`; a unit
can have state, durable findings, both, or neither.

### 1. Locate the mined artifacts

Same mechanics as Part A step 2 (bounded depth 3, skip vendored dirs, skip linked worktrees, flag unversioned units) but against `mines_durable` instead of `reads_back`. This can surface units Part A never sees: for the Code front, `Code/AGENTS.md` and `Code/REFERENCE.md` sit at the sibling root itself, so the sibling root is a unit here even though it holds no `CONTEXT.md` and is invisible to state sync.

### 2. Extract candidates

Read each mined artifact and pull out discrete claims: a gotcha, a workaround, a "never do X" rule, a decision with its reasoning, a trap already hit once. One candidate per claim, not per section: split a bullet list of five gotchas into five candidates so each can be filtered, routed, and deduplicated independently.

### 3. Admission filter: the volume is the enemy

Keep a candidate only if it passes all three. Guarding all three matters because saving everything defeats the purpose as completely as saving nothing:

- **Not discoverable by reading the code.** If opening the file in question would tell a future reader the same thing in the same amount of time, it does not belong in the vault.
- **Generalizes past one component.** A fact that only ever matters inside a single function or a single file is not durable knowledge; it is a code comment that has not been written yet.
- **The obvious approach is wrong.** The candidate exists because someone tried the naive thing and it failed. A fact with no trap behind it is documentation, not a finding.

Drop anything that fails a leg. Emphasis in the source ("IMPORTANT", bold, all-caps) is not evidence of durability and never substitutes for the filter.

### 4. Propose a scope, never decide it alone

For each surviving candidate, propose one of three levels and give the one-sentence reasoning:

- **Project**: bites only inside this unit. Default level, written without confirmation.
- **Stack**: would bite any project sharing this unit's stack (same framework, same runtime quirk, same shared infra). Needs the user's confirmation before the first write; state the proposed stack slug and why.
- **Universal**: holds regardless of stack (a methodology point, a review discipline, a decision-making rule). Needs confirmation like Stack, and a stronger justification, since this is the level where an over-eager promotion pollutes every project the vault serves.

Never promote silently. A candidate proposed at Stack or Universal and not yet confirmed gets written at Project level only, flagged as pending promotion, and listed in the summary for the user to confirm or correct. Confirming a pending promotion later moves it: the full text goes to the new level, the project note is left with a one-line pointer instead of the full text.

### 5. Never duplicate: search before writing

Before writing a confirmed candidate, search the destination file for the same claim by topic, not by exact wording. For a Stack candidate, also check other projects' `LEARNINGS.md` for the same stack in case the same trap was already promoted from a different origin. If found, update that entry in place (extend its provenance list, correct anything the new source contradicts) instead of appending a second entry. Two copies of the same finding drift the moment one gets corrected and the other does not, which is worse than writing it once.

### 6. Write, with provenance, one canonical copy

Destinations mirror the vault's existing tiers: project detail stays with the project, broader knowledge climbs into `05-knowledge/` the same way `knowledge-consolidation` already promotes personal insight into `05-knowledge/consolidated/`:

- **Project** → `vault/04-projects/<unit-slug>/LEARNINGS.md`
- **Stack** → `vault/05-knowledge/stacks/<stack-slug>.md` (new folder, one file per stack, created on first promotion)
- **Universal** → `vault/05-knowledge/consolidated/engineering-principles-framework.md`, using the same `consolidated-knowledge` frontmatter `knowledge-consolidation` already writes for frameworks, with `domain: "engineering"` and `framework: "engineering-principles"`. A universal finding is a framework like any other the vault holds, not a new document type.

Once a finding is promoted past Project, its full text lives only at the promoted level; the project note keeps a pointer, never a second full copy. This is what step 5's "never duplicate" rule requires in practice.

Each note opens with light frontmatter (`type: durable-findings`, `scope: project|stack|universal`, `last_updated`) and one heading per finding. Every finding carries a provenance line:

`[Source: <front_id>/<unit-slug> | YYYY-MM-DD | confidence: high|medium|low]`

Confidence follows Part A's rule: `high` when quoted, `medium` when inferred, `low` when the source is ambiguous. A promoted finding keeps every origin's provenance line and gains the promotion date; it never loses where it came from.

### 7. What this pass never does

- **It never edits or deletes the source.** Mining is read-and-cite, exactly like state sync: `AGENTS.md`/`REFERENCE.md` stay exactly what they already are.
- **It never promotes past Project on its own judgment.** See step 4.
- **It never feeds the state note.** A mined artifact does not describe "current state," even for a unit that also has `CONTEXT.md`.

### 8. Summarize for the human

Report per front: candidates extracted, candidates dropped by the filter (and which leg), findings written at each level, findings updated in place, and every pending promotion awaiting confirmation. Lead with pending promotions: those are the ones that need the user's decision before this pass is actually done.

## What this skill does NOT do

- **It does not do the front's work.** It reads what the front's methodology already wrote. If the software front's artifacts are stale, the fix is to run devaing, not to have Brainia infer project state.
- **It does not write outside `writes_to`.** A front declares where its knowledge lands; this skill respects it.
- **It does not touch the sibling folder.** Read-only, always. This includes `mines_durable` artifacts, which are mined, never edited.
- **It does not invent state.** If an artifact does not say it, the note does not claim it.
- **It does not save every candidate it finds.** A candidate that fails the admission filter is dropped, not stored "just in case."
- **It does not decide a promotion above Project by itself.** It proposes; the user confirms.

## Success criteria

Sync is successful when:
1. Every active front with a non-empty `reads_back` or `mines_durable` was visited
2. Every note carries a source citation with a real date per factual claim
3. No source artifact was copied or moved into the vault
4. Every contradiction between a prior note and the current artifact was corrected and reported
5. Missing artifacts were reported rather than filled in with inference
6. The sibling folders are byte-for-byte unchanged
7. Every durable finding kept passed all three admission-filter legs
8. No finding was promoted past Project scope without the user's confirmation
9. No finding exists at more than one level after the run. Promotion left a pointer, not a copy

## Error Handling

- **`active_fronts` missing** — send the user to `/onboarding`, do not guess the fronts.
- **Front pack missing for an active front** — a front with no pack is valid and simply has nothing to sync. Skip it silently.
- **`writes_to` path absent** — create it, since it is inside the vault and declared by the pack.
- **Sibling folder absent** — report it. The front may have been renamed or moved, which is normal and is the user's call, not something to auto-correct.
- **Artifact unparseable** — record what could be read, flag the rest, never fabricate the gap.
- **`mines_durable` absent**: that front simply has no durable-knowledge pass this run. State sync still runs if `reads_back` is set. Skip Part B silently, same as a missing front pack.
- **A pending promotion from a prior run is never confirmed**: leave it pending indefinitely. It is already safely stored at Project level; there is no deadline that forces a decision.

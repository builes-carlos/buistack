## Sub-agent invocation

Steps that say "Spawn a sub-agent" or "invoke Agent":
- **Claude Code**: use the `Agent` tool (no `isolation` parameter — work in current directory).
- **Other environments (Codex, Aider, Cursor, etc.)**: read `subagent_cli:` from `.devaing.md`. Default: `claude -p --model claude-sonnet-4-6`. Build the prompt and pipe it: `IMPLEMENTATION_REPORT=$(echo "$PROMPT" | $SUBAGENT_CLI)`.

For adversarial review and the data integrity check, Claude Code can additionally use `subagent_type=compound-engineering:ce-adversarial-reviewer` / `ce-data-integrity-guardian` — but only when that plugin is actually present. This is a suggestion with a fallback, never a requirement: check live before each use, do not assume it's there just because the session is Claude Code.

**Availability check:** `claude plugin list 2>/dev/null | grep -q "compound-engineering" && echo present || echo absent`. Do this check independently at each of the two sites below (Step 3) rather than trusting a flag from `devaing-init` — the plugin can be installed or removed after init ran.

- **present:** spawn Agent with the matching `subagent_type`, passing the prompt built at that site.
- **absent:** spawn a plain Agent (no `subagent_type`) with that same prompt text as its instructions — the identical inline prompt other environments pipe through `subagent_cli`. Tell the user once per run: "compound-engineering not installed — running the review inline."

# devaing-work

Two lanes, chosen at the start:

- **Backlog** — implement GitHub issues on epic branches. One person per epic (lock by issue assignment). PRs created and merged to the phase integration branch when the epic closes; `devaing-ship` merges the phase branch to main and deploys.
- **Direct** — implement something now on a branch from main, with no issue and no active phase required. The PR merges straight to main; `devaing-ship` deploys.

## Opening — Route

Before reading `## Phases` or fetching issues, ask how this session should run:

```
How do you want to work?

  1. Backlog — pick from the open issues
  2. Direct  — implement something now, outside the backlog
```

Wait for response.

**If 2 (Direct):** skip to [Direct flow](#direct-flow). Do not read `## Phases`, do not fetch issues.

**If 1 (Backlog):** continue to Issue selection below.

Skip this prompt entirely when the skill was invoked with an explicit `#N` or `<milestone>` argument — that is already a Backlog choice.

**When there is no active phase:** if `CONTEXT.md ## Phases` has no row with Status `In Progress`, or the file has no `## Phases` section at all, Backlog has nothing to offer. Do not stall or error. Say so and go Direct:

```
No active phase in CONTEXT.md — the backlog has nothing to pick from.
Going Direct.
```

This is the normal state for a project that works incrementally instead of in phases. Direct is a first-class lane, not a fallback.

## Opening — Issue selection

Fetch open issues grouped by milestone:

```bash
gh issue list --state open --json number,title,milestone,assignees --jq 'sort_by(.number)'
```

Identify the active phase from `CONTEXT.md ## Phases` (the row with Status `In Progress`). All issues in milestones of that phase are READY. Extract the phase number from that row. Store as `<phase-num>`. The integration branch for this phase is `phase-<phase-num>`.

For each milestone in the active phase, compute its owner — the assignee of any open or recently-closed issue in that milestone:

```bash
gh issue list --milestone "<milestone>" --state all --json assignees \
  --jq '[.[] | select(.assignees | length > 0) | .assignees[0].login] | unique'
```

Display grouped by epic, numeric order within each, with owner if any:

```
Open tasks — Phase "<phase-name>"

  Epic "Auth" — owned by @userA
    #3   Login form UI
    #4   JWT middleware
    #5   Session refresh

  Epic "Billing" — no owner yet
    #6   Pricing table
    #7   Checkout flow

How do you want to work?

  1. One     — pick a task
  2. All     — implement all your epic's tasks in sequence
  3. Cascade — implement, close epic, take next available epic, repeat
  4. Direct  — implement something outside the backlog
```

Wait for response.

**If 4 (Direct):** skip to [Direct flow](#direct-flow).

**If 1 (One):** ask which number, then continue to Step 1.

**If 2 (All):** identify the epic for the chosen first issue. Collect all open issues in that milestone sorted by number. Run Step 1 through Step 3 for each in sequence. Then run Closing logic.

**If 3 (Cascade):** repeat until zero open issues remain in the phase:
1. Identify next available epic for the current user (epic with no assignee yet, OR epic where current user is already the owner). If no available epic: stop and report which epics are owned by other users.
2. Run Step 1 through Step 3 for each open issue in that milestone in numeric order.
3. When milestone closes, repeat from 1.

## Step 1 — Resolve and claim the issue

```bash
gh issue view <N> --comments
```

Read the full issue: what to build, acceptance criteria. Verify the milestone (epic).

**Epic ownership check:**

```bash
gh issue list --milestone "<milestone>" --state all --json assignees \
  --jq '[.[] | select(.assignees | length > 0) | .assignees[0].login] | unique'
```

If the list contains any user other than the current GitHub user (`gh api user --jq '.login'`):

```
⚠ Epic "<milestone>" is owned by @<userA>.
Pick a different epic, or coordinate with @<userA> first.

Available epics for you: <list of milestones in current phase with no other-owner assignment>.

Take this one anyway? (y/n)
```

If user says no: stop and let them re-run.

**Assign the issue and move card:**

```bash
gh issue edit <N> --add-assignee @me
```

**Lazy branch creation/checkout:**

Derive a slug from the milestone name (lowercase, replace non-alphanumeric with `-`, collapse repeated dashes, strip leading/trailing dashes). Store as `<slug>`.

```bash
git fetch origin
LOCAL=$(git branch --list epic/<slug>)
REMOTE=$(git ls-remote --heads origin epic/<slug>)
```

- Both empty: create new branch from the phase integration branch.
  ```bash
  git checkout phase-<phase-num> && git pull
  git checkout -b epic/<slug>
  git push -u origin epic/<slug>
  ```
- Local exists: `git checkout epic/<slug>` (no rebase — one person per epic).
- Only remote: `git checkout -t origin/epic/<slug>`.

## Step 2 — Implement via sub-agent

Check for prototype and design system:

```bash
ls prototype/ 2>/dev/null || ls src/prototype/ 2>/dev/null
```

Read DESIGN.md if it exists at the project root.

Build a **filtered** CONTEXT for the sub-agent: include only `## Project`, `## Domain glossary`, `## Architecture`, `## Key constraints`. Exclude `## Phases`, `## Next phase backlog`, and any compressed milestone history (reduces tokens, focuses the agent).

Spawn an Agent (no `isolation` parameter — work in current directory on the active epic branch) with this prompt:

> You are implementing GitHub issue #<N> for the project "<name>".
>
> **Project context (filtered):**
> <filtered CONTEXT.md content>
>
> **Issue:**
> <full issue content including acceptance criteria>
>
> **Design system:** <DESIGN.md content if exists, otherwise "none — use existing project styles">
>
> **Prototype screen for this slice:** <relevant prototype file content if found, otherwise "none">
>
> **Instructions:**
> - You are on branch `epic/<slug>`. Commit your changes on this branch. Do NOT switch branches, do NOT merge, do NOT open a PR.
> - If a prototype screen exists for this issue, replace it with real implementation. Leave all other prototype screens as mocks.
> - Follow design tokens in DESIGN.md if present. Do not invent a design system.
> - **Tests** — write tests only when:
>   (a) the code has complex business logic with branching or combinatorics (pricing, state machines, validation rules, parsing),
>   (b) the issue is fixing a bug — add one regression test that reproduces the bug,
>   (c) the code is async or non-clickable (cron, webhook, background job),
>   (d) the issue's acceptance criteria explicitly requests a test.
>   Otherwise: don't.
>   When you do write tests: test behavior, not implementation. 1 happy path + 1 critical edge case. Same commit as the feature.
> - Run existing tests after implementing (`npm test`, `pytest`, etc.) to confirm nothing broke.
> - Stage and commit all changes: `git commit -m "feat: <short description> (closes #<N>)"`. Do not commit .env files or secrets.
> - Report back: what you built, any non-obvious decisions, anything knowingly left incomplete.

Wait for the sub-agent to complete. Capture its report as `<implementation-report>`.

## Step 3 — Post-implementation

**Self-verification:**

Detect the test command from the project root:

- Node: check if `package.json` has a `"test"` script → `npm test`
- Python: check for `pytest.ini` or `[tool.pytest.ini_options]` in `pyproject.toml` → `pytest`
- Rust: `cargo test`
- Other: skip silently

If a test command is detected, run it. If exit code ≠ 0:

```
⚠ Tests failing after sub-agent commit.
<last 30 lines of output>

Options:
  1. Fix now    — spawn sub-agent to fix the failures
  2. Document   — add to CONTEXT.md Known limitations and continue
  3. Revert     — git reset --hard HEAD~1 (discards the commit)
```

Wait for response.
- "Fix now": spawn a sub-agent (same structure as Step 2) with the test output as the task. Commit the fix, re-run tests. Repeat up to 2 times.
- "Document": continue — the failure will go into Known limitations below.
- "Revert": run `git reset --hard HEAD~1`. Stop and return to issue selection.

**AC validation:** read the issue body with `gh issue view <N>`. Extract all `- [ ]` lines from `## Acceptance criteria`.

If the issue has no Acceptance criteria section, or the extraction is empty: skip this step silently.

If there are criteria: cross-check each one against `<implementation-report>` from Step 2 — what the sub-agent reported as built vs. left incomplete.

- All criteria covered per the report: continue without asking.
  ```
  Acceptance criteria: N/N covered per the implementation report.
  ```
- Any criterion not covered, or the report doesn't make it possible to tell: stop and show which:
  ```
  Acceptance criteria check for #<N>:
    [ ] <AC not covered 1>
    [ ] <AC not covered 2>
    ...
  ```
  Offer Fix now / Document / Revert (same flow as test failure above).

**Data integrity check (conditional):**

```bash
MIGRATION_FILES=$(git diff HEAD~1..HEAD --name-only | grep -E "(migration|prisma/|db/seeds)" | wc -l)
```

If `MIGRATION_FILES` > 0:

```bash
MIGRATION_DIFF=$(git diff HEAD~1..HEAD -- $(git diff HEAD~1..HEAD --name-only | grep -E "(migration|prisma/|db/seeds)"))
```

Build the review prompt:

```
INTEGRITY_PROMPT="You are reviewing a database migration diff for production safety.

Diff to review:
$MIGRATION_DIFF

Check for:
- Missing NOT NULL constraints on columns with existing rows (will fail unless a default is provided)
- Unsafe column drops or type changes that truncate or corrupt existing data
- Missing indexes on new foreign keys
- Multi-step operations not wrapped in a transaction
- Seed data that could cause unique constraint violations on re-run (must use upsert)
- Any operation that cannot be rolled back safely

Report findings as HIGH / MEDIUM / LOW:
- HIGH: data loss or production migration failure risk
- MEDIUM: integrity or performance risk that may not surface immediately
- LOW: non-critical issue

For each finding: one-line description + concrete failure scenario."
```

**Claude Code:** check availability as described in "Sub-agent invocation" above. If present, spawn Agent with `subagent_type=compound-engineering:ce-data-integrity-guardian`, passing the prompt above. If absent, spawn a plain Agent with the same prompt above as its instructions, and say so.

**Other environments:**
```bash
SUBAGENT_CLI=$(grep "^subagent_cli:" .devaing.md | sed 's/subagent_cli: *//' 2>/dev/null || echo "claude -p --model claude-sonnet-4-6")
INTEGRITY_REPORT=$(echo "$INTEGRITY_PROMPT" | $SUBAGENT_CLI)
```

Process findings the same way as adversarial review findings below (HIGH per-finding, MEDIUM/LOW as table).

**Adversarial review:**

Check whether this is the last open issue in the milestone:

```bash
OPEN_IN_MILESTONE=$(gh issue list --milestone "<milestone>" --state open \
  --json number --jq 'length')
```

Decide automatically from `OPEN_IN_MILESTONE` — do not ask:
- `OPEN_IN_MILESTONE` = 0 (last issue in the milestone): run the review.
  ```
  Adversarial review: running (last issue in milestone).
  ```
- `OPEN_IN_MILESTONE` > 0: skip it.
  ```
  Adversarial review: skipped (<OPEN_IN_MILESTONE> issues still open in milestone).
  ```

The user can still ask for it explicitly at any point, even when it would otherwise be skipped.

If running: get the full epic diff:

```bash
# For epic close (OPEN_IN_MILESTONE = 0): review the entire epic
REVIEW_DIFF=$(git diff phase-<phase-num>..epic/<slug>)
REVIEW_SCOPE="the full epic branch `epic/<slug>` (all commits, not just the last)"

# For intermediate issues (OPEN_IN_MILESTONE > 0): review only this commit
REVIEW_DIFF=$(git diff HEAD~1..HEAD)
REVIEW_SCOPE="the commit closing GitHub issue #<N>"
```

Build the review prompt:

```
ADVERSARIAL_PROMPT="You are an adversarial code reviewer. Your goal is to break the implementation —
not check against known patterns, but actively construct failure scenarios.

Reviewing: <REVIEW_SCOPE> ('<title>')
Acceptance criteria: <criteria>

Diff:
$REVIEW_DIFF

For each changed component:
1. What is the intended behavior?
2. Construct at least one concrete scenario where this implementation fails silently,
   fails incorrectly, or produces wrong output under real-world conditions
   (concurrent users, partial failures, edge case inputs, timing issues, missing data).
3. Is there a race condition, state mutation, unhandled error path, or incorrect
   assumption baked in?

Do NOT list what the code does. Find where it breaks.

Report findings as HIGH / MEDIUM / LOW:
- HIGH: exploitable, causes data loss, or silent corruption
- MEDIUM: incorrect behavior under non-trivial conditions
- LOW: minor reliability concern or edge case

For each finding: one-line description + the specific failure scenario."
```

**Claude Code:** check availability as described in "Sub-agent invocation" above. If present, spawn Agent with `subagent_type=compound-engineering:ce-adversarial-reviewer`, passing the prompt above. If absent, spawn a plain Agent with the same prompt above as its instructions, and say so.

**Other environments:**
```bash
SUBAGENT_CLI=$(grep "^subagent_cli:" .devaing.md | sed 's/subagent_cli: *//' 2>/dev/null || echo "claude -p --model claude-sonnet-4-6")
ADVERSARIAL_REPORT=$(echo "$ADVERSARIAL_PROMPT" | $SUBAGENT_CLI)
```

Process findings:
- HIGH findings: for each one, ask:
  ```
  HIGH: <finding>
  Fix now / Document in Known limitations / Ignore? (f/d/i)
  ```
  "Fix now": spawn sub-agent, commit fix as `fix: address adversarial review finding (#<N>)`.
- MEDIUM/LOW findings: show as a table, ask once:
  ```
  MEDIUM/LOW findings:
  | Severity | Finding |
  |---|---|
  | MEDIUM | <...> |
  | LOW | <...> |

  Document all in Known limitations? (y/n)
  ```

**CONTEXT.md update:**
- New domain terms: add rows to `## Domain glossary`.
- Architecture changes: **edit the existing `## Architecture` section surgically** — update the description to reflect current state. Do not append; rewrite the affected sentence or paragraph.
- New integrations or key constraints: add to the relevant section.
- Feature implementation details (file paths, SQL specifics, edge cases, state machines): write to `docs/features/<slug>.md`. Do NOT put implementation detail in CONTEXT.md.
- Index that feature doc in CONTEXT.md **reusing the index the project already has**. Find it before writing: `grep -n "docs/features/" CONTEXT.md`. If a section already links to `docs/features/` — whatever it is called (`## Áreas de producto`, `## Features implemented`, a table, a bullet list) — add the entry inside that section, matching its existing format (same table columns, or same bullet shape). Only when no such section exists, create `## Features implemented` with: `- **<Feature name>**: one-line description → \`docs/features/<slug>.md\``. Never create a second index next to one that already exists.
- Only update what actually changed. Do not rewrite the whole file.

**Known limitations:** if the report mentions anything intentionally left incomplete or broken, decide where it belongs before writing:

- **Scoped to one product area** → append it to that area's `docs/features/<slug>.md`, not to CONTEXT.md.
- **Cross-cutting** (hits several areas or the app as a whole) → add it to CONTEXT.md's known-limitations section, matching the heading the project actually uses. It may carry a qualifier (e.g. `## Known limitations (transversales)`); use the existing heading, do not create a second one.

Use this shape either way:

```
- **<what>**: <description>. Deferred because: <reason>. Triggered by: <condition>. For now: <guidance>.
```

**Tactical anti-patterns capture (conditional):**

Derive automatically from what this Step 3 already produced: `<implementation-report>` from Step 2, and the findings from the adversarial review and the data integrity check (if they ran). Look for a fix that corrected a plausible-but-wrong pattern, a workaround that must not be replicated, or a subtle incorrect assumption an adversarial finding revealed.

If a clear anti-pattern surfaces: append to `CLAUDE.md ## Tactical anti-patterns`:

```
- **<name>**: <what the wrong pattern looks like> → <correct pattern>. [Why: <one-line reason>]
```

Tell the user in one line what was added:
```
Tactical anti-pattern captured: <name>.
```

If nothing surfaces, continue silently.

**Commit project docs:** if CONTEXT.md, any file under `docs/features/`, or CLAUDE.md (anti-pattern) changed:

```bash
git add CONTEXT.md 2>/dev/null
git add docs/features/ 2>/dev/null
git add CLAUDE.md 2>/dev/null
git commit -m "docs: update project docs after #<N>"
```

**Push epic branch:**

```bash
git push origin epic/<slug>
```

**Close the issue:**

```bash
git rev-parse --short HEAD | xargs -I{} gh issue close <N> --comment "Implemented in {}. CONTEXT.md updated."
```

## Closing — Epic complete check

Check if the milestone has 0 open issues:

```bash
OPEN_IN_MILESTONE=$(gh issue list --milestone "<milestone>" --state open \
  --json number --jq 'length')
```

If `OPEN_IN_MILESTONE` > 0: skip to "Per-issue close" below.

If 0 (epic complete):

1. **Known limitations review:** check whether this epic resolved any existing limitations:

   ```bash
   grep -A 200 "^## Known limitations" CONTEXT.md | grep "^\- \*\*"
   ```

   If there are no entries: skip this step silently.

   If there are entries: spawn a sub-agent with (a) the list of limitations and (b) the full epic diff (`REVIEW_DIFF` from the adversarial review step above, or `git diff phase-<phase-num>..epic/<slug>` if that step didn't run). Ask it to report which of these limitations were resolved by this epic, with concrete evidence from the diff for each.

   If the sub-agent finds none resolved: continue silently.

   If it finds candidates: show them with their evidence and confirm before touching CONTEXT.md:
   ```
   Known limitations resolved by this epic:
     - <limitation 1> — <evidence>
     - <limitation 2> — <evidence>

   Remove these from CONTEXT.md? (y/n)
   ```

   If confirmed: remove or update them in CONTEXT.md. Commit:
   ```bash
   git add CONTEXT.md
   git commit -m "docs: resolve known limitations addressed in epic/<slug>"
   git push
   ```

3. Create PR from `epic/<slug>` to main:
   ```bash
   CLOSED_ISSUES=$(gh issue list --milestone "<milestone>" --state closed \
     --json number --jq '[.[] | "#\(.number)"] | join(", ")')
   PR_URL=$(gh pr create --base phase-<phase-num> --head epic/<slug> \
     --title "Epic: <milestone>" \
     --body "Closes milestone '<milestone>'. Issues: $CLOSED_ISSUES")
   ```

4. Auto-merge the PR to main (one dev owns the epic, no peer review by default — real QA happens at phase end):
   ```bash
   PR_NUMBER=$(echo "$PR_URL" | grep -o '[0-9]*$')
   gh pr merge $PR_NUMBER --merge --delete-branch
   ```

5. Sync local main:
   ```bash
   git checkout main && git pull
   ```

## Closing — Phase complete check

After the epic close (or if epic still has open issues, after the per-issue close), check if ALL milestones in the active phase have 0 open issues:

```bash
OPEN_IN_PHASE=$(gh issue list --state open --json number,milestone \
  --jq '[.[] | select(.milestone != null)] | length')
```

If `OPEN_IN_PHASE` > 0:

```
✓ #<N> done.

  → Next: /devaing-work
```

If 0 (phase complete): update `CONTEXT.md ## Phases` — change current phase Status to `Complete`. Commit + push:

```bash
git add CONTEXT.md
git commit -m "docs: Phase <N> complete"
git push
```

**Architecture review (suggestion with fallback, not a requirement):** ask before the closing message below.

```
Phase "<phase-name>" complete. Look for architecture drift before shipping? (y/n)
```

If no: skip silently, continue to Output.

If yes, check availability: an `improve-codebase-architecture` skill listed among this session's available skills, or `$HOME/.claude/skills/improve-codebase-architecture/SKILL.md` on disk.

- **present:** invoke `improve-codebase-architecture`.
- **absent:** run the review yourself. Read `CONTEXT.md`'s domain glossary and any ADRs in the areas this phase touched, then look across the phase's epics for shallow modules (interface nearly as complex as the implementation) and tightly-coupled pieces. Apply the deletion test to anything suspect: would removing it concentrate complexity elsewhere, or just move it? Present any real candidate (files, problem, proposed change, benefit) and let the user pick before touching code. Tell the user once: "improve-codebase-architecture not installed — running the review inline."

Output:

```
╔══════════════════════════════════════════════════════════════╗
║  Phase "<phase-name>" complete.                              ║
╚══════════════════════════════════════════════════════════════╝

QA en main local antes de shipear. Todo el código de la fase ya está mergeado.

  → Findings: /devaing-bug "..." o /devaing-phase-revise
  → Cuando estés listo: /devaing-ship
```

## Direct flow

```
What do you want to build or fix?
```

Wait. Store as `<direct-description>`.

Direct flow does not use epic branches. It works directly on a branch from main:

```bash
git checkout main && git pull
SLUG=$(echo "<direct-description>" | tr '[:upper:]' '[:lower:]' \
  | sed 's/[^a-z0-9]/-/g' | sed 's/-\+/-/g' | sed 's/^-\|-$//g' | cut -c1-50)
git checkout -b hotfix/$SLUG
```

Spawn a sub-agent (same structure as Step 2) but pass `<direct-description>` instead of an issue. Commit message: conventional prefix matching what the work actually is (`feat:`, `fix:`, `docs:`, `chore:`), then a short description.

After sub-agent completes: run Step 3 (CONTEXT.md update + push). Push hotfix branch:

```bash
git push origin hotfix/$SLUG
```

Create and auto-merge a PR to main:

```bash
PR_URL=$(gh pr create --base main --head hotfix/$SLUG \
  --title "<direct-description>" \
  --body "Implemented directly. No issue tracked.")
PR_NUMBER=$(echo "$PR_URL" | grep -o '[0-9]*$')
gh pr merge $PR_NUMBER --merge --delete-branch
git checkout main && git pull
```

Output:

```
✓ Done.

  → When ready to deploy to prod: /devaing-ship
```

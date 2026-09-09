# Doctrine, the software half

How software gets built with agents. This is the instrumentation of the universal
doctrine in `harnessing/`, which is the authority and is never repeated here. If a rule
below reads like it would apply to any kind of work, it is in the wrong file.

Two role names appear throughout. `Faber` is the one who builds. `Testarossa` is the one
who verifies against the requirement rather than against the implementation. Their full
definition, their lifetime and their model live in `harnessing/doctrine/universal.md`.

## Risk decides rigor

Before starting, the question that changes everything is whether the work is going to
production or is going to be looked at.

**Mock or demo.** No tests, no type checks, no lint. Done means it looks right.

**Production.** Full rigor. Tests written to break the thing. Review in fresh context.
Verification measured, not assumed.

If the level is not clear, ask before starting. It is one question and it changes the
cost of everything after it.

## Specification

**A spec is a disposable contract.** It governs while the slice is being built, then it
gets folded into the area document and deleted. Two living documents describing the
same thing will disagree, and nobody will know which one is current.

**One document per product area, never one per story.**

[Why: a project that kept one living document per user story ended up with 99 files and
433,000 words. Two documents in the same repository gave two different counts for the
same thing, 42 and 95, and both were checked in.]

**Acceptance criteria go in EARS.** A trigger and a response: WHEN or IF or WHILE or
WHERE something happens, THE SYSTEM SHALL do something. A criterion without a trigger is
a wish.

**Anything checkable by a regular expression goes to a lint in CI**, not to an agent
asked to count it. Missing sections, broken links, leftover TBDs.

[Why: 191 lines of standard library hold five invariants on every push, with no session
present and no tokens spent.]

**A claim in a spec about how existing code behaves needs a file and line citation.**
Without one it is a guess, and the guess governs the build.

**Before designing anything that discriminates over a dimension, inventory that
dimension in full.** A gate, a feature flag, a cutoff.

[Why: a notification module shipped with a toggle that had no effect on seventeen of the
notification types, because the toggle was designed before anyone counted them.]

## Slices

**One vertical slice at a time.** Never two in the same working tree.

**An isolated worktree per slice** when the slice is real: several files, lasts a while,
can be left half done. A three-line fix does not need one.

**An issue is a tool, not a rite.** It is worth opening when the work has to be resumed
in another session or handed to someone else. For a two-minute fix it is overhead.

**The phase plan lives in a project document, not scattered across issues.**

**A human closes the issue.** The agent leaves it ready to test and stops there.

## Building

**Change only what the slice requires.** No refactoring outside scope. No obvious
comments. Ask before adding a dependency.

**A silent catch is not a fix.** If it fails without the user finding out, the visible
surface of the error is part of the fix.

**Look at the screen before handing over a UI change.** Bring up the browser and look.
A green suite and a green build do not know what the page looks like.

**A data problem is diagnosed with the rows.** Not with a theory about timestamps.
Pull the actual records and read them.

**Do not call a fix done without exercising it.** Run the exact case. If it was a data
problem, correct the affected rows in the same session.

**When debugging with temporary logging, leave it in until the bug is confirmed gone.**

## Tests

Three layers, each with a different owner, because the person who wrote the code is not
a good judge of whether it is right.

**Layer 1, `Faber`.** Runs its own gates before handing anything over: type check, the
suite. It is an obligation, not a request, and it is not delegated.

**Layer 2, `Testarossa`.** Tests against the requirement, never against the
implementation, and sweeps in the opposite direction from whoever built it. Looking for
what is missing, not confirming what is there.

**Layer 3, the lead.** Reads the diff.

**The automated test is written by the agent, always, in the same slice and the same
commit as the code.** Not in a follow-up.

**A test has to die with the mutant.** Break by hand the thing it claims to protect,
confirm the test fails, put it back. A test that passes against broken code is worse
than no test, because it buys confidence it has not earned.

**Do not pad with speculative tests outside the scope asked for.**

[Why: a suite of 1052 tests was green while eight form fields were never being sent.
Every one of those tests asserted what the code did.]

**Review in fresh context** when the slice touches authentication, money, data
mutations or migrations, or when it runs past roughly 300 lines. Below that,
self-review is enough. Whoever reviews is told to break the invariant, not to confirm
the happy path.

**Verification is sized to the change.** Only the gates that could fail because of what
was touched. A trivial check, two numbers or one grep, is done inline and not dispatched
at all.

## Documentation

**Code and the document that governs it stay in sync in the same task**, in both
directions.

**`Faber` updates the area document in its own commit.** The lead owns the spec. Method
rules are written only by the lead and a change is approved by the person.

**The top-level document drifts in silence.** When a cross-cutting fact changes, search
the top-level document for the old claim.

[Why: two documents in the same repository stated 42 and 95 for the same count, because
one was updated and the other was not.]

## Enforcement

Instruction is not enforcement, and that rule is in `harnessing/`. Here is what it means
for a repository.

**The teeth live at the merge boundary.** Rules are declared where every agent reads
them, but what must not rot is forced in CI, which runs with no session present. That is
the whole point: when someone merges from their laptop, no skill is running.

**A red workflow blocks nothing by itself.** People merge anyway. It blocks only when it
is a required status check in branch protection, which is repository configuration, not
workflow configuration.

**A skill can create the gate and can never be the gate.** It writes the workflow,
generates the check scripts into the repository, and sets branch protection. If the
logic lived inside the skill it would be instruction again.

**A feed gate can be gamed** by touching the living document with an empty line. It
raises the floor. It does not manufacture care. Say so when proposing one.

## Git

**`git stash` is invisible.** Commit to a throwaway branch instead, `wip/<topic>-<date>`.
Run `git stash list` at the start of any non-trivial session, because someone else's
stash is someone else's lost work.

**Resolving a conflict and committing are two steps, never chained.** Check that no
marker survived before committing.

**Commit and push only when the person asks.** If the current branch is the deploy
branch, branch first. A push to production triggers a deploy and never happens without
an explicit order.

**The commit message is written by the agent and captures the structural reason for the
change**, not the list of files touched. The file list is already in the diff.

## Security

**Never commit an environment file.** The anonymous key belongs in the frontend, the
service role key only in the backend, and a database password is never exposed to a
client.

**Always an ORM or parameterized queries.** Never string concatenation into a query.

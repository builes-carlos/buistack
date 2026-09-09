# Sources

Where the ideas in this stack came from, what survived, and what was dropped.

Two things get confused often enough to be worth separating here.

**A dependency** is third-party code that has to be installed for something to work.
It costs: it can vanish, it can drift under an upstream update, it can break a phase
halfway through. Dependencies are declared by the module that has them, so devaing
lists its own in `devaing/STRATEGY.md`.

**Provenance** is where an idea came from. It costs nothing and needs no maintenance.
It is written down for two reasons: a rule without its origin gets relitigated, and a
public framework owes attribution.

This file is provenance. Nothing listed here has to be installed for this stack to
work.

## Matt Pocock's skills

**Kept:** atomic issues, isolated worktrees, an ADR written after implementing rather
than before, vertical slices. devaing also invokes five of these skills when they are
present, and falls back to an inline prompt when they are not. That makes them
suggestions, not requirements, and `devaing/STRATEGY.md` lists them.

**Dropped:** `to-prd` and `to-issues`, because `devaing-phase-def` already generates
issues from a defined phase. `tdd`, because it duplicates the three test layers, each
with a different owner.

## gstack (Garry Tan, MIT)

**Kept:** the feed-forward pipeline where each step writes what the next one consumes.
Chaining roles instead of convening them. Prototyping before committing to a UI. And
the checkpoint, reworked into mid-flight recovery, because a session dies in the
middle of a slice and the work should not have to start over.

Plus `office-hours`, which is no longer a dependency. It is a self-contained file in
`harnessing/skills/office-hours/`, stripped of gstack's infrastructure (telemetry,
gbrain, plan tuning, mockups, cross-model calls), with its attribution inside the
file. It asks for two tools and nothing else.

**Dropped:** `/autoplan`, `/plan-ceo-review`, `/plan-design-review`, `/plan-eng-review`.
All four are review by a panel of role personas, which this doctrine rejects by name:
a panel produces agreement, not scrutiny, and pays for one context per reviewer. Also
dropped: taste learning, multi-model validation, and safety gates.

## GSD

**Kept:** the context rot model. Quality peaks in the first 30% of a context window,
rushes past 50%, and hallucinates past 70%. That model is baked into the progressive
mode, into the context budget warning, and into the rule that a closed slice gets a
fresh session. Zero code, zero installation.

**Dropped:** autonomous next-step detection, and keeping REQUIREMENTS, STATE and
ROADMAP as separate files. One living document per project holds all three, because
three files drift against each other and nobody notices which one is stale.

## Compound Engineering

**Kept:** three review agents, invoked by devaing when present. Nothing from its
design side.

**Dropped:** `ce-work` and `ce-frontend-design`, no longer in use. A `docs/solutions/`
directory as a knowledge store, which contradicts both one document per area and the
admission filter: a store that accepts everything is a store nobody reads. Panels of N
reviewers, and scored rubrics.

## Superpowers

**Kept: nothing.** It is listed here because it was adopted once and then reverted,
and a reversion without its reason gets proposed again.

It was adopted in a methodology document to solve one thing: starting from a
description instead of a ticket. That requirement is real and it still stands. It is
now met by the Direct lane of `devaing-work`, which starts from a description, needs
no issue and no active phase, and is a first-class lane rather than a fallback. So the
reason to adopt it is gone, and what remains is the cost.

Two of its distinctive choices are deliberate differences here, not gaps:

**Its mandatory double gate** (spec compliance plus code quality, both must pass) is a
panel. This stack uses the lean version: the builder runs its own gates before
handing off, the tester checks against the requirement rather than the
implementation, and the lead reads the diff.

**Its decomposition into two-to-five-minute tasks with a fresh subagent per task** is
the most expensive topology available. Every task pays to read the world again: the
instruction chain, the context document, the area docs, and only then the code. That
is tens of thousands of tokens before any work happens. Here the unit is the slice,
and an agent lives a whole slice.

[Why: on one session, four files were touched by six different agents, each reading
them from scratch. The waste was invisible per dispatch and only showed up when the
bill was added together.]

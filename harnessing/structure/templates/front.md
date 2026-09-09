<!--
Template: front layer.
Exists when one domain of life or work is managed apart from the others
(software, health, finances, a specific client). Copy this into that
front's own folder as its AGENTS.md (or equivalent) and fill in the
sections. Delete this comment block once filled in.

What this file holds: which module this front delegates execution to, and
how to detect whether that module is actually present.
What it never holds: rules that belong to one specific project inside the
front. Those go in that project's own layer.
-->

# <front name>

## What this front covers

<!-- one or two sentences: what falls under this front and what does not -->

## Delegates to

<!-- which module or framework does the actual work for this front, e.g.
     "devaing, one instance per project under this folder" or
     "brainia's <front-id> pack" -->

## How to detect it is present

<!--
Concrete check, not a guess: a marker file, a directory, a skill installed
under ~/.claude/skills/. Whatever reads this front's rules should be able
to run this check and get a yes/no, and treat "no" as information rather
than a failure.
-->

## Project-specific rules

None here by design. If a rule only applies to one project under this
front, it lives in that project's own `AGENTS.md`, not here.

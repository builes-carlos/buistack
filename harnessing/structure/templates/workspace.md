<!--
Template: workspace layer.
Exists when several projects share one machine. Copy this into the
workspace root (e.g. the folder that holds every project's own folder as a
sibling) as AGENTS.md and fill in the sections that apply. Delete any
section that does not apply on this machine, and delete this comment block
once filled in.

What this file holds: machine and environment facts that would bite in any
project on this machine, and only those.
What it never holds: doctrine (that is harnessing's job, loaded separately),
or anything specific to one machine that would not travel if the workspace
moved to a different machine (a login the workspace holder no longer uses,
a path that only existed on a laptop that got replaced).
-->

# Workspace: <name>

Machine and environment facts shared by every project under this folder.
Nothing here is method; that is loaded from harnessing separately.

## Disk and cache layout

<!-- where large caches, downloads, and package manager stores are
     redirected on this machine, and why -->

## Automation browser

<!-- which browser automation should drive on this machine, and any quirk
     that makes the obvious choice wrong (a stub launcher, a profile lock) -->

## Per-project accounts

<!-- table: project or path glob -> which account (git host, cloud, etc)
     applies there, and why mixing them up breaks something -->

## Worktrees

<!-- convention for where parallel worktrees get created on this machine,
     and the rule for when a branch needs its own worktree versus when a
     branch alone is enough -->

## Known quirks of shared tooling

<!-- anything that fails silently and would otherwise get re-discovered by
     every project on this machine independently -->

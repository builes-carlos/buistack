<!--
Template: project layer, AGENTS.md.
This layer always exists, for every project. This file is what a
tool-agnostic agent reads: commands, where things live, and gotchas that
are specific to this one project. Delete this comment block once filled
in.

If this project uses devaing, devaing-init writes the execution section of
this file already (issue tracker, triage labels, domain docs, the
devaing-work invocation). Add the sections below around that, do not
replace what devaing wrote.
-->

# AGENTS.md (<project name>)

Tool-agnostic. Any agent working in this project reads this file plus
everything above it in the directory tree (workspace, front, personal
root, wherever those layers exist on this machine).

## Commands

<!-- how to run, test, build, lint this project. The commands an agent
     would otherwise have to guess or rediscover by reading package files -->

## Where things live

<!-- the map a new agent needs before touching code: where config lives,
     where the entry point is, where generated code should never be
     hand-edited -->

## Project-specific gotchas

<!--
Only what is specific to this project. A gotcha that would bite in any
project on the same stack belongs at the workspace layer instead, not
here (see harnessing/structure/README.md's admission filter).
-->

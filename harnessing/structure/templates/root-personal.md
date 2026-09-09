<!--
Template: personal root layer.
Exists when more than one front is in play. Copy this to the container root
(e.g. `AGENTS.md` at the top of the machine's project tree) and fill in the
table. Delete this comment block once filled in.

What this file holds: a pointer to the fronts, nothing else.
What it never holds: method. Method lives in harnessing's doctrine, loaded
from wherever the install put the pointer, not repeated here.
-->

# Fronts

This machine separates life and work into fronts. Each front is a sibling
folder; this file only says which fronts exist and where each one's own
rules live. Nothing about how to work lives here.

| Front | Path | Delegates to |
|---|---|---|
| <!-- e.g. Code --> | <!-- e.g. Code/ --> | <!-- e.g. devaing, per project --> |
| <!-- e.g. Health --> | <!-- e.g. Health/ --> | <!-- e.g. brainia front pack --> |

See `<path to harnessing instance>/` for the machine-wide doctrine pointer
and hook registration, and each front's own file for what it owns.

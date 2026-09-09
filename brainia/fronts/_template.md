---
front_id: my-front
display_name: My Front
aliases: []
sibling: MyFront/
writes_to: []
methodology: none
reads_back: []
skills: []
profiles: []
integrations: []
---

# Front Pack: My Front

> Copy this file, rename it to `your-front-id.md`, and customize the sections below.
> The `front_id` must be lowercase with hyphens. `aliases` are container sibling folder names
> (case-insensitive) that should resolve to this front.

## Field reference

| Field | Meaning |
|---|---|
| `front_id` | Stable id, kebab-case (e.g. `code`). |
| `display_name` | Human name (e.g. `Code`). |
| `aliases` | Container sibling folder names that map to this front. |
| `sibling` | The container-relative folder this front owns (e.g. `Code/`). |
| `writes_to` | Vault paths this front's knowledge lands in. |
| `methodology` | External tool this front delegates execution to, or `none`. |
| `reads_back` | Artifacts Brainia ingests from the sibling folder. |
| `skills` | Front-owned skills staged under `fronts/<id>/skills/`. Empty for most fronts. |
| `profiles` | Optional sub-profiles inside the front (see `fronts/_profile-template.md`). |
| `integrations` | Integrations that only make sense for this front. |

## What a front is

A front is a **life domain** — the highest level at which the user organizes their life. It is
NOT a project and NOT a tool. `Brain/` itself is not a front; it is the engine that thinks
across all of them.

## The two core rules

1. **The core never asks what the user does for a living.** Fronts are detected from the
   filesystem — the presence of a sibling folder next to `Brain/` — never from an onboarding
   question about job or role. A new sibling folder appearing is the model working as intended.
2. **The core contains no domain tooling.** A front that needs execution machinery (build,
   ship, review) points its `methodology` field at an external tool that already does that job.
   It never bundles one. Brainia reads back the artifacts that tool produces; it does not
   replace the tool.

## This directory is not the registry of fronts

**The filesystem is the source of truth for which fronts exist, not `fronts/`.** A sibling
folder next to `Brain/` is a front whether or not a pack file for it exists here.

A pack file in `fronts/` is **optional** — it exists only when a front needs something declared:
an external `methodology` to delegate to, front-owned `skills`, front-local `profiles`, or a
non-obvious `writes_to` mapping. A front with no pack file works fine and must never be treated
as unconfigured, unratified, or invalid.

The set of fronts is **open and mutable**: fronts are added, renamed, merged, and dropped over
the life of the second brain, same as onboarding suggestions are never a fixed taxonomy. Nothing
in this directory may require ratifying the set, and no code path should reject or block on a
front that has no pack here.

## Notes

*Add any front-specific tips or context here.*

# TODO / Roadmap

## Two engines, one mentor (planned)

This project (`Brainia`) is the `Brain/` of an `AI-Coached-Life` container (see README "Where this fits"). It is **engine-agnostic**: a second brain configured as a life-coach mentor, independent of which underlying framework powers it. The engine brand lives inside `Brain/`; the container does not carry it.

There are two engine forks:

- **COG** — current engine. Everything in this repo today runs on the COG fork ([huytieu/COG-second-brain](https://github.com/huytieu/COG-second-brain), tracked as the `upstream` remote). Complete and working now.
- **gbrain / "second brain"** — future personalized engine. Not built yet. **TO-DO.**

Today the entire mentor lives on the COG fork. The gbrain-based variant is planned and will be added later. Keep the framing engine-agnostic so the switch (or coexistence) is clean when gbrain is ready.

## Fronts architecture — done

The core is now domain-agnostic. Onboarding resolves fronts from the filesystem instead of asking for a job title, the six software role packs became front-local profiles, and the seven PM/delivery skills moved into `fronts/work/skills/`. The software front delegates to devaing and owns no development tooling. See the "Front packs" section of `CLAUDE.md` for the contract.

## Deferred, on purpose

- **Selective import from COG 3.9.** Upstream is four releases ahead (`.agents/` universal agent surface, `memory-hygiene`, `daily-journal`, `.claude/lib/`). Those pieces are agnostic and worth taking. The V-model development harness (`closed-loop`, `retro`, `ultragoal`, `loop-engineering`, `review-cockpit`) and the design/content skills are **not**: they are exactly the domain tooling the core just shed. Any future pull must be selective, never a wholesale rebase.
- **`brainia-update.sh` awareness of `fronts/`.** The script compares framework files by path and knows nothing about the fronts tree. Only matters when a pull from upstream actually happens.
- **Front-owned skill activation mechanics.** Copy is the current design (mirroring `devaing/install.sh` and `global-hooks/install.py`). Symlinks may be better; not decided.
- **COG rename — done except issue/discussion links.** `COG-VERSION` → `BRAINIA-VERSION`, `cog-update.sh` → `brainia-update.sh`, the `update-cog` skill id → `update-brainia`, and the Kiro `cog-<name>` power prefixes → `brainia-<name>` are all renamed. The GitHub issue/discussion links in `CONTRIBUTING.md` still point at upstream (`huytieu/COG-second-brain`) by design — that is genuinely where framework updates come from.
- **Publishing.** No marketplace entry, no third-party install path, no example fronts beyond the real ones. The trigger to generalize is a **second** front delegating to a second external methodology with zero core changes. Until that happens, the architecture is unproven and this stays personal.

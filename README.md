# buistack

Three frameworks for working with AI agents. Each one is effective on its own.
Together they cover the loop from "should this exist" to "it is in production and
what was learned is written down".

| Framework | What it governs |
|---|---|
| [harnessing](harnessing/) | How anything gets dispatched to an agent: the doctrine, the stage-to-owner map, the `.md` hierarchy, the module contract |
| [devaing](devaing/) | Building software: phases, epics, vertical slices, tests, the road to production |
| [brainia](brainia/) | The human's own operating system: a vault, life and work fronts, durable memory |

## The contract between them

**They suggest each other. They never require each other.** A module that is absent
is information, not an error. Adopt one, two, or all three, and each delivers its
full value alone.

That is a discipline, not an accident of packaging, so it is written down in
`harnessing/` and checked by `harnessing-audit`.

## Install

Each folder installs on its own and documents how in its own README. Clone the repo
and run the install of the one you want.

In Claude Code the repo is also a plugin marketplace, so a single framework can be
installed without the other two. Outside Claude Code, and devaing runs in Codex and
Cursor as well, the install is the clone plus the folder's own installer.

## Versions

Versioned per folder, not collapsed into one number: tags are prefixed
(`devaing-v…`, `brainia-v…`, `harnessing-v…`). Touching the doctrine must not bump
brainia.

## License

MIT, except where a folder carries its own notice.

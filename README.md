# buistack

Three frameworks for working with AI agents. Each one is effective on its own.
Together they cover the loop from "should this exist" to "it is in production and what
was learned is written down".

| Framework | What it governs | Take it if |
|---|---|---|
| [harnessing](harnessing/) | How anything gets dispatched to an agent: the doctrine, the stage-to-owner map, the `.md` hierarchy | Your agent keeps doing things you did not ask for, forgetting what it already learned, or burning a fortune on work you could have done inline |
| [devaing](devaing/) | Building software: phases, epics, vertical slices, tests, the road to production | You are building something real and the second session always costs more than the first |
| [brainia](brainia/) | The human's own operating system: a vault, life and work fronts, durable memory | You want what you learn to survive the session it happened in |

## Start here

If you only take one, take **harnessing**. It is the smallest, it needs nothing else,
and it changes every session you have afterwards rather than only the ones about code.

```bash
git clone https://github.com/builes-carlos/buistack.git
cd buistack/harnessing
python install.py --check     # reports what it would do, writes nothing
python install.py             # doctrine into your agent's files, plus three skills
```

Restart your agent. From then on the doctrine loads in every session without anyone
invoking it, which is the whole point: a rule you have to remember to look up is a rule
you will skip exactly when it matters.

Then read [`harnessing/doctrine/universal.md`](harnessing/doctrine/universal.md)
yourself, once. It is the argument, and you should disagree with parts of it.

For the other two, each folder's README has its own install. In Claude Code the repo is
also a plugin marketplace, so you can take one without the other two:

```bash
claude plugin marketplace add builes-carlos/buistack
claude plugin install devaing@buistack
```

Outside Claude Code, and devaing runs in Codex and Cursor too, install is the clone
plus the folder's own installer.

## What you are agreeing to

**They suggest each other. They never require each other.** A module that is absent is
information, not an error. Adopt one, two, or all three, and each delivers its full
value alone. That is a discipline rather than an accident of packaging, so it is
written down in `harnessing/` and checked by `harnessing-audit`.

**None of this is a product.** It is one person's working method, made generic enough
to hand over. The rules that survived are the ones that cost something to learn, and
most carry a `[Why:]` with the incident and the number behind them. Where a rule does
not fit how you work, the profile template is the seam: change it there, not in the
framework.

**Your own configuration never lives in this repo.** It goes in an instance folder
named `<framework>-<yourname>`, kept wherever you like. `harnessing-init` scaffolds it
and stops, with no opinion about whether you version it, sync it, or leave it alone.

## Versions

Versioned per folder rather than collapsed into one number, with prefixed tags
(`devaing-v…`, `brainia-v…`, `harnessing-v…`). Touching the doctrine must not bump
brainia.

## License

MIT, except where a folder carries its own notice. brainia derives from
[COG](https://github.com/huytieu/COG-second-brain) and keeps its original copyright.

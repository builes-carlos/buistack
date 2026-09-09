---
name: harnessing-init
description: Set up a harnessing instance on this machine. Detects agents, existing structure, and other modules without asking. Asks exactly three questions and one confirmation. Use when the user wants to install harnessing, set up the agent doctrine on a new machine, or re-run setup after a prior partial install.
---

# harnessing-init

**Budget: three questions and one confirmation. Not one more.** Everything
else in this skill is detection. If a step below is tempted to ask something
it can instead find out by looking at the filesystem, look instead of
asking.

## Step 0: Bootstrap check

```bash
ls ~/.claude/skills/harnessing-init 2>/dev/null && echo "bootstrapped" || echo "not bootstrapped"
```

If `not bootstrapped`, this skill is somehow running without having been
installed by `install.py` first (a user ran the SKILL.md directly from the
clone). Continue anyway, since running from the clone works, but note it in
the final report.

## Step 1: Detect, silently, before asking anything

Run every check below before producing any output.

**Which agents are on this machine:**

```bash
for d in ~/.claude ~/.codex ~/.gemini; do
  [ -d "$d" ] && echo "present: $d"
done
```

Only the agents found here get files written to them in Step 6. This is not
a question, it decides scope, not the user's preference.

**Whether devaing and brainia are present:**

```bash
# devaing: look for its skills, installed globally
ls ~/.claude/skills/devaing-* -d 2>/dev/null
# brainia: look for a sibling folder whose contents mark it as a brain
# (a vault/ dir alongside .claude/skills/), walking up from cwd
```

Report what is found. **Never install either.** An absent module is
information, not a gap this skill fixes.

**Whether this is a re-run:**

```bash
grep -rl "harnessing:start" . 2>/dev/null | head -5
```

If any file already carries the harnessing marker block, this is a re-run.
Read the existing block(s) to recover the prior instance path and profile
location, and skip straight to Step 5 (confirm the tree, nothing more to
ask) unless the recovered state is incomplete, in which case fill only the
missing piece silently. **Never ask the user to re-answer something a prior
run already answered and left on disk.** They do not remember what the old
template looked like, and asking them to reconcile it just leaks the
skill's own internal bookkeeping onto them.

**Which layers already exist, walking up the tree:**

```bash
dir="$PWD"
while [ "$dir" != "/" ] && [ "$dir" != "$(dirname "$dir")" ]; do
  for f in AGENTS.md CLAUDE.md; do
    [ -f "$dir/$f" ] && echo "found: $dir/$f"
  done
  [ -d "$dir/vault" ] && echo "found vault: $dir/vault"
  dir="$(dirname "$dir")"
done
```

On Windows, walk up with the equivalent of `Split-Path` instead of
`dirname`; the loop's job is the same regardless of shell.

Also list sibling directories of the current one, since a personal-root or
front layer usually shows up as a sibling, not a parent, of wherever this
skill was invoked from.

**Which `.md` files already exist at each candidate layer:**

For every layer identified above, check whether its file already has
content (not a placeholder) before proposing to touch it. **Never overwrite
one that exists.** Record it as "already there" for the confirmation in
Step 5.

## Step 2: Question 1: profile

```
What language and register should agents use with you, and are there any
hard constraints they should never cross without asking first (e.g. never
touch a production database, never message a third party on your behalf)?
```

Store the answer. Do not ask follow-ups here; whatever level of detail comes
back is what goes in the profile file. `profile/_template.md` (from this
clone) is the shape; more can be added to the instance's profile file later
by hand, this question does not need to extract everything up front.

## Step 3: Propose the tree, then confirm (the one confirmation)

Based on Step 1's detection, propose a concrete shape, not an open question:

```
Here is what I found:
  - <N> agent(s) on this machine: <list>
  - devaing: <present at <path> | not found>
  - brainia: <present at <path> | not found>
  - Existing layers: <list what Step 1 found, or "none">

I'll set up harnessing at <proposed layer, e.g. "the workspace root,
Code/AGENTS.md and Code/CLAUDE.md"> and put your instance at
<proposed instance path>.

Sound right, or should it go somewhere else?
```

Wait for a yes or a correction. If corrected, use the corrected path for
everything below. This is the only confirmation in the budget: it is not a
second profile question, it is ratifying or adjusting what detection
already found.

## Step 4: Question 2: instance location and name

Skip if the re-run path in Step 1 already recovered this.

```bash
git config user.name 2>/dev/null
```

```
Where should your harnessing instance live, and what should it be called?
Default: <parent of the confirmed layer>/harnessing-<git user.name, lowercased
and hyphenated>
```

Offer the default as a plain enter. Store the confirmed path as
`<instance_path>`.

## Step 5: Question 3: the SessionStart hook

```
Register a Claude Code SessionStart hook that injects the condensed
doctrine into every session on this machine, regardless of which project
is open? This writes to ~/.claude/settings.json (merged, nothing else in
that file is touched). (y/n, default y)
```

Claude Code only. If no `~/.claude` was detected in Step 1, skip this
question entirely, there is nothing to register a hook into.

## Step 6: Scaffold

This is where state actually changes. Everything above was detection and
confirmation.

1. Create `<instance_path>/` if it does not exist.
2. Copy `profile/_template.md` into `<instance_path>/profile.md`, and fill
   in the sections from Step 2's answer.
3. For each layer confirmed in Step 3 that does not already have its file
   (Step 1 checked this): copy the matching template from
   `structure/templates/` and note it as scaffolded. For each layer that
   already had a file: leave it untouched, note it as "left as is".
4. Run the installer for each detected agent and confirmed layer:

```bash
python <path to this clone>/install.py --path <confirmed layer path> \
  $([ "<hook answer>" = "n" ] && echo --skip-hook)
```

5. If this is a re-run (Step 1), migrate silently: update the doctrine
   pointer block in place (the installer already does this idempotently),
   and do not re-ask anything Step 1 already recovered.

## Step 7: Stop here

**Do not create a remote for the instance.** Creating a private remote repo
is a state change with its own blast radius (a new repo under the user's
account), and it needs an explicit go, not an inference from "the user ran
init." Report that the instance folder is scaffolded locally and that
creating a remote, if wanted, is a separate step.

## Final report

```
harnessing instance: <instance_path>
Profile: written from your answer / already existed, left as is
Layers scaffolded: <list, or "none, everything already existed">
Layers left untouched (already had content): <list, or "none">
Agents configured: <list>
devaing: <present, not touched | not found>
brainia: <present, not touched | not found>
SessionStart hook: registered / skipped (no y) / skipped (no ~/.claude)

Instance folder is local only. Say the word if you want a private remote
for it.
```

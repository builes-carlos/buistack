---
name: onboarding
description: Personalize Brainia for your workflow - creates profile, interests, and watchlist files with guided setup (run this first!)
front: all
integrations: []
---

# Brainia Onboarding Skill

## Purpose
Welcome new users and collect essential information to personalize their Brainia experience. All configuration is stored as natural markdown files within the vault structure, following Brainia's philosophy of transparent, editable knowledge.

## When to Invoke
- User explicitly requests `/onboarding` or mentions "onboarding" or "setup Brainia"
- User is new and hasn't completed onboarding yet
- User wants to update their profile or add new projects
- Any time profile customization is needed

## Core Design Principle: Smart, Low-Friction Onboarding

**The onboarding MUST feel like a natural conversation, NOT a form to fill out.**

Key rules:
- **Ask open-ended questions, not option-pickers.** Never present numbered lists of choices for the user to pick from.
- **Ask as few questions as possible.** Infer what you can from context and the user's natural responses.
- **Never ask redundant questions.** If you can extract the answer from something the user already said, don't ask again.
- **Parse intelligently.** If someone says "I'm Alex, a midwife, following the WHO perinatal guidelines", extract: name=Alex, occupation=midwife (optional context), watchlist=[WHO guidelines]. Don't ask follow-up questions for info already given, and never ask for occupation at all.
- **Confirm, don't re-ask.** If you're unsure about something the user said, confirm your interpretation rather than asking the question fresh.

## Process Flow

### 0. Install the global guard hook (Claude Code only)

On the Claude Code surface, before anything else, install the bulk-extraction
guard as a machine-global hook so it applies in every session — this vertical,
the container root, and any sibling `Code/` project opened directly — not only
when Claude is opened at the container root:

```bash
python global-hooks/install.py
```

Idempotent and safe to re-run. It copies `global-hooks/guard-bulk-extraction.py`
into `~/.claude/hooks/` and registers a `PreToolUse(Read)` hook in
`~/.claude/settings.json` without touching unrelated settings. Skip on Kiro and
Gemini — those surfaces don't use Claude Code's `settings.json` hooks.

### 1. Welcome Message
Greet the user warmly and explain what Brainia is:
```
Welcome to Brainia - your self-evolving second brain powered by Claude + Obsidian + Git!

Brainia helps you capture thoughts, get daily intelligence briefings, and build knowledge over time - all stored as simple markdown files you own.

Let's get you set up. Tell me a bit about yourself - your name, what you do, and what topics or areas you're most interested in staying sharp on. Feel free to share as much or as little as you'd like.
```

**This single open-ended prompt replaces the old sequential questions.** The user can naturally mention their name, occupation, interests, sources, projects, and competitors all at once - or just share a few things.

### 2. Check for Existing Profile

Look for `vault/00-inbox/MY-PROFILE.md`. If it exists:
```
I found an existing Brainia profile! What would you like to update? Just tell me what you'd like to change - your interests, projects, profile info, or anything else.
```

**Don't present a numbered menu.** Let them describe what they want in natural language.

### 3. Intelligent Information Extraction

After the user responds, extract as much as possible from their natural language:

| Field | How to Extract |
|-------|---------------|
| **Name** | Look for self-introduction patterns ("I'm Alex", "My name is...", "Call me..."). Use first name by default. |
| **Occupation** | *Optional context only.* If they volunteer what they do, keep it as free text. Never ask for it, never gate anything on it, never use it to decide which skills they get. |
| **Interests** | Look for topic mentions ("interested in AI", "following crypto", "love design"). Also infer from whatever context they gave. |
| **News Sources** | Look for source mentions ("I read HN", "follow on Twitter"). If not mentioned, skip - it's optional. |
| **Projects** | Look for project mentions ("working on a SaaS app", "building..."). If not mentioned, skip. |
| **Competitive Watch** | Look for company/person mentions ("tracking Stripe", "watching what OpenAI does"). If not mentioned, skip. |

### 4. Smart Follow-Up (Only If Needed)

After extracting what you can, check what's missing from the **required** fields only:
- **Name** (required)
- **Interests** (required - need at least 2-3 topics)

Occupation is **not** a required field and never generates a follow-up. Nothing in Brainia depends on knowing what the user does for a living.

If any required field is missing, ask ONE follow-up that covers all gaps. For example:
```
Thanks! I got your name. What topics are you most interested in staying updated on? (e.g., AI, startups, design, health - whatever matters to you)
```

**Optional fields** (news sources, projects, competitive watch) should NEVER generate follow-up questions. If the user didn't mention them, skip them. They can always add them later by editing the files or running onboarding again.

### 5. Confirm and Create

Before creating files, briefly confirm what you captured, ask what they'd like to name their assistant, and ask about agent team mode:
```
Here's what I've got:

- **Name**: Alex
- **Occupation**: Midwife at a public hospital *(optional, only because they mentioned it)*
- **Interests**: Perinatal care research, nutrition, hospital policy, choral music
- **Projects**: Rewriting the ward's intake protocol
- **Tracking**: WHO guidelines, two research groups

(Deliberately not a software job. If your examples are all engineers and PMs, the skill teaches the
opposite of the rule above.)

Two quick things before I set up your vault:

**1. What would you like to call me?** This becomes your assistant's name and I'll answer to it from here on. Default is **Brainia** - but pick anything that fits (Jarvis, Mneme, Sage, your call).

**2. How should I work?** I can run in two modes:
- **Solo mode** (default): I handle everything directly in our conversation.
- **Agent team mode**: I delegate research, analysis, and writing to specialist sub-agents for deeper, more thorough results. Works best with Claude Code.

(Solo is great for most people - team mode is for power users who want maximum depth.)
```

**Wait for confirmation**, then generate everything. If they say "looks good" or similar, proceed. If they correct something, update and proceed without re-confirming. Default to `solo` for agent mode and **Brainia** for the assistant name if they don't express a preference.

### 5.5. Front Resolution

Fronts are detected from the **filesystem**, never from a job interview. **Never ask what the user does for a living in order to unlock functionality, and never reduce what they get based on their occupation.** A nurse, a teacher and a staff engineer all receive the same full core.

1. List the sibling folders of the brain in the container root. Skip dotfiles.

   **Identify the brain by its contents, not by its name.** The README shows it cloned as `Brain/`, but a real instance may be named anything (`brainia-alex/`, `my-brain/`). The brain is the sibling that contains a `vault/` directory alongside `.claude/skills/`. Excluding it matters because **Brain is not a front**: it is the engine that thinks across all of them. A name-only check silently turns the brain into an eleventh front.

   Anything else at the container root is a candidate front, including things that look like stray repos or tooling. Do not filter them out on your own judgment: list them and let the user say what to ignore in step 4. A folder you think is "not a life domain" may be exactly how they organize one.
2. For each sibling, scan `fronts/*.md` and match the folder name (case-insensitive) against `front_id` and `aliases` in the pack's YAML frontmatter.
3. **A sibling with no matching pack is still a front.** Record it. Never call it unconfigured, never ask the user to justify it, never drop it from the list.
4. Present the detected set for correction, not for ratification:
   ```
   I can see these fronts in your life container:

   Code, Strategy, Health, Finances, People

   Anything there I should ignore, or a front you keep somewhere else?
   ```
5. Store the confirmed list as `active_fronts` in the MY-PROFILE.md frontmatter.
6. For each active front whose pack declares `skills`: those live in `fronts/<id>/skills/` and are copied into `.claude/skills/` on activation. Offer it, never activate unasked, and never activate skills belonging to an inactive front.
7. For each active front whose pack declares a `methodology`: check whether the external tool is present and report what you found. **Do not install it.** Example — the software front delegates to devaing, detected by `devaing-*` directories in `~/.claude/skills/`. If it is missing, say where it lives and how to install it, then move on.
8. If a pack declares `profiles`, those order recommendations *inside* that front only. Do not surface them during onboarding and never require one.
9. If any active front declares a non-empty `reads_back`, tell the user that `/front-sync` pulls those artifacts into the vault, and offer to run it once now. Do not run it unasked.

**There is no fallback branch.** No "custom" state, no reduced skill set, no consolation tier. Capture, synthesis and knowledge are core and work for everyone, whatever their fronts turn out to be.

### 5.6. Integration Discovery

After front resolution, set up the user's integration preferences:

1. If any active front's pack declares `integrations`, present those with front-specific context:
   ```
   Based on your fronts, these integrations would give Brainia the most context:

   [For each integration declared by an active front:]
   - **[Integration]** — [Why it matters for that front]

   Which of these do you already use? And are there any other tools you'd like to connect?
   ```

2. Parse the user's response:
   - Services they confirm using → add to **Active** section of MY-INTEGRATIONS.md
   - Services they don't mention or say no to → add to **Disabled** section
   - Additional services they mention → add to **Active** section
   - Always add `ElevenLabs` to **Disabled** unless explicitly requested

3. Generate `vault/00-inbox/MY-INTEGRATIONS.md`:
   ```markdown
   ---
   type: integrations
   created: YYYY-MM-DD
   tags: ["#integrations", "#config", "#brainia"]
   ---

   # My Integrations

   *Brainia checks this file before using any external service. Edit anytime.*

   ## Active
   [For each confirmed integration:]
   - **[Service]**: [Brief description of how Brainia uses it]

   ## Disabled
   [For each declined/unmentioned integration:]
   - **[Service]**: Skipped during onboarding. Enable anytime by moving to Active section.

   ---

   *Move services between Active and Disabled sections to control what Brainia connects to.*
   ```

4. If no active front declares integrations, ask conversationally without presuming a domain:
   ```
   Brainia can connect to outside tools to pull in more context. Do you use anything you'd like me to read from? (Totally optional - Brainia works great without them too.)
   ```
   Do not recite a list of software-industry tools here. Let the user name their own.

### 6. Generate Profile Documents

Create the following markdown files:

#### `vault/00-inbox/MY-PROFILE.md`
```markdown
---
type: profile
created: YYYY-MM-DD
onboarding_completed: true
assistant_name: [chosen name, default "Brainia"]
active_fronts: [detected front ids, e.g. code, health, finances]
agent_mode: [solo or team]
tags: ["#profile", "#config", "#brainia"]
---

# My Brainia Profile

## About Me
- **Name**: [Name]
- **Occupation**: [Only if volunteered — free text, never a gate]
- **Active Fronts**: [Detected life fronts]
- **Profile Created**: [Date]

## Settings
- **Assistant Name**: [name] *(what you call me; I answer to this)*
- **Agent Mode**: [solo/team] *(solo = handle everything directly; team = delegate to specialist sub-agents for deeper results)*

## Active Projects
[If they mentioned projects:]
- [[vault/04-projects/[slug]/PROJECT-OVERVIEW|Project Name 1]]
- [[vault/04-projects/[slug]/PROJECT-OVERVIEW|Project Name 2]]

[If no projects:]
*No active projects yet. Add them anytime by editing this file or running onboarding again.*

## Related
- [[MY-INTERESTS|My Interests & News Sources]]
- [[vault/03-professional/COMPETITIVE-WATCHLIST|Competitive Watchlist]] *(if applicable)*

## Notes
*Feel free to add notes here about your Brainia usage, preferences, or anything else.*

---

*Edit this file anytime to update your profile. Brainia reads it when you use skills.*
```

#### `vault/00-inbox/MY-INTERESTS.md`
```markdown
---
type: interests
created: YYYY-MM-DD
tags: ["#interests", "#daily-brief", "#config"]
---

# My Interests & News Sources

*These topics guide my daily intelligence briefings.*

## Topics I'm Interested In
- [Topic 1]
- [Topic 2]
- [Topic 3]
- [Topic 4]
- [Topic 5]

## Preferred News Sources
[If sources were mentioned:]
*Where I like to get information:*
- [Source 1]
- [Source 2]
- [Source 3]

[If no sources mentioned:]
*No specific sources set. Brainia will search broadly for your topics. Add preferred sources here anytime.*

## Notes
*Add any additional context about your interests here.*

---

*Update this file anytime as your interests evolve. Just edit and save—Brainia will pick up the changes.*
```

#### `vault/03-professional/COMPETITIVE-WATCHLIST.md` (only if they mentioned companies/people to track)
```markdown
---
type: competitive-intelligence
created: YYYY-MM-DD
tags: ["#competitive", "#intelligence", "#tracking"]
---

# Competitive Watchlist

*Companies, people, or organizations I'm keeping an eye on.*

## Watching
- [Company/Person 1]
- [Company/Person 2]
- [Company/Person 3]

## Why I'm Tracking Them
*Add context here about why these matter to you or your projects.*

---

*When you mention these in braindumps, Brainia will automatically extract the intel to your project competitive folders.*
```

#### For Each Project: `vault/04-projects/[project-slug]/PROJECT-OVERVIEW.md`
```markdown
---
type: project-overview
project: [project-name]
slug: [project-slug]
created: YYYY-MM-DD
status: active
tags: ["#project", "#overview"]
---

# [Project Name]

## What is this project?
[Brief description - leave for user to fill in]

## Current Status
*What phase are you in? What's happening now?*

## Project Resources
- [[braindumps/|Project Braindumps]]
- [[competitive/|Competitive Intelligence]]
- [[content/|Content & Assets]]
- [[planning/|Planning Documents]]

## Next Steps
- [ ] [Action item 1]
- [ ] [Action item 2]

---

*This overview helps Brainia organize your project-related thoughts and updates.*
```

### 7. Create Directory Structure
Based on configuration, create personalized structure:

**Base Structure (Always):**
```
vault/00-inbox/
vault/01-daily/
  briefs/
  checkins/
vault/02-personal/
  braindumps/
  development/
  wellness/
vault/03-professional/
  braindumps/
  leadership/
  strategy/
  skills/
vault/04-projects/
vault/05-knowledge/
  consolidated/
  patterns/
  timeline/
  booklets/
06-templates/
```

**Project-Specific (For each listed project):**
```
vault/04-projects/[project-slug]/
  PROJECT-OVERVIEW.md
  braindumps/
  competitive/
  content/
  planning/
  resources/
```

### 8. Create Welcome Guide

Generate: `vault/00-inbox/WELCOME-TO-BRAINIA.md`

```markdown
---
type: guide
created: YYYY-MM-DD
tags: ["#welcome", "#getting-started", "#brainia"]
---

# Welcome to Your Second Brain, [Name]! I'm [assistant_name].

Your Brainia is now personalized and ready to use. Here's how to get started:

## Your Profile Documents

I've created these documents to store your preferences:

- **[[MY-PROFILE]]** - Your basic info, active fronts, and workflow preferences
- **[[MY-INTERESTS]]** - Topics for your daily briefs
- **[[MY-INTEGRATIONS]]** - Your active and disabled integrations
- **[[vault/03-professional/COMPETITIVE-WATCHLIST]]** - Companies you're tracking *(if applicable)*

**You can edit these files anytime.** Brainia reads them when you use skills, so your changes take effect immediately.

## Your Skills

These are the core skills. They work the same for everyone, whatever your fronts are:

1. **daily-brief** — Personalized news intelligence
2. **braindump** — Capture and classify thoughts
3. **weekly-checkin** — Weekly pattern analysis
4. **knowledge-consolidation** — Build frameworks from scattered notes
5. **url-dump** — Save URLs with auto-extracted insights
6. **scout** — Triage a URL or tool before saving it
7. **update-brainia** — Keep the framework current

[If any active front declares skills or a methodology, add a section per front:]

## Your Fronts

[For each active front, one short block:]
- **[Front display name]** — [what Brainia does for this front]
  - [If the pack declares `skills`: list them and note they were activated into `.claude/skills/`]
  - [If the pack declares a `methodology`: name the external tool, its entry command, and whether it was detected. Example: the software front hands off to devaing — start with `/devaing-director`.]

[Fronts with no pack, or a pack that declares neither, are still listed. They simply have no extra tooling, which is normal.]

## Your Integrations

[If integrations were configured:]
**Active**: [List active integrations]
**Disabled**: [List disabled integrations]

You can change these anytime by editing [[MY-INTEGRATIONS]].

[If no integrations configured:]
No integrations configured yet. Brainia works great standalone — add integrations anytime by editing `vault/00-inbox/MY-INTEGRATIONS.md`.

## Quick Start

### 1. Daily Morning Routine
Invoke the daily-brief skill to get your personalized intelligence briefing covering:
[List their selected interest areas]

### 2. Capture Your Thoughts
Use the braindump skill to quickly capture ideas, insights, and thoughts. Your braindumps will automatically be categorized into:
[List their focus domains]

Choose from your active projects:
[List their projects with links]

### 3. Weekly Reflection
Every week, use the weekly-checkin skill to review your week's insights and patterns.

## Your Active Projects

[If they have projects]
You're tracking these projects:
- [[vault/04-projects/[slug]/PROJECT-OVERVIEW|Project 1]]
- [[vault/04-projects/[slug]/PROJECT-OVERVIEW|Project 2]]

When you use the braindump skill, select the project to automatically file your thoughts in the right place.

## How Brainia Uses Your Profile

**Daily Briefs**: Uses [[MY-INTERESTS]] to curate relevant news
**Braindumps**: Offers your projects from [[MY-PROFILE]] as options
**Competitive Intel**: Auto-extracts mentions of companies in [[COMPETITIVE-WATCHLIST]]
**Weekly Check-ins**: Reviews progress across your domains

## Next Steps

1. **Try your first braindump**: Use the braindump skill and start writing
2. **Get your daily brief**: Invoke the daily-brief skill to see curated intelligence
3. **Explore your vault**: All your files are organized in the sidebar
4. **Edit your profile**: Open [[MY-PROFILE]] and customize anytime

## Keeping COG Updated

COG separates your content from framework files. When new versions are released:
- Run `/update-brainia` to check for and apply updates
- Or use the shell script: `./brainia-update.sh --check`
- Your braindumps, profiles, and notes are **never** touched by updates

Check your current version: `cat BRAINIA-VERSION`

## Tips for Success

- **Don't overthink it**: Just dump your thoughts, Brainia will help organize
- **Be consistent**: Daily briefs and braindumps work best as habits
- **Review weekly**: Use the weekly-checkin skill to see patterns emerge
- **Evolve your setup**: Edit your profile files anytime or run onboarding again to add projects
- **Stay updated**: Run `/update-brainia` periodically to get new skills and improvements

## Getting Help

- Check `SETUP.md` for detailed guides
- Visit the GitHub repo for documentation

**Your second brain is learning about you. Let's begin!**

---

*You can archive or delete this welcome guide once you're comfortable with Brainia.*
```

### 9. Wrap-Up (No Menu!)
After setup, summarize what was created and suggest a natural next action:

```
You're all set! I've created your profile, interests, and project files. Everything is in your vault and editable anytime.

If you want to jump right in, try a braindump - just tell me what's on your mind and I'll capture it. Or ask for your daily brief to see what's happening in your interest areas today.
```

**Don't present a numbered menu of next actions.** Just suggest one or two natural things and let them decide.

## Configuration Update Mode

If user runs onboarding after initial setup (MY-PROFILE.md exists):

Don't show a menu. Just ask:
```
You've already completed onboarding! What would you like to update? Just tell me what needs changing.
```

Then intelligently handle whatever they say - whether it's adding projects, changing interests, updating their role, etc.

## Success Criteria

Onboarding is successful when:
1. `MY-PROFILE.md` created in `vault/00-inbox/` with `active_fronts` and `assistant_name` in frontmatter
2. `MY-INTERESTS.md` created in `vault/00-inbox/`
3. `MY-INTEGRATIONS.md` created in `vault/00-inbox/` with active/disabled sections
4. Fronts resolved from the filesystem, confirmed with the user, and stored — including any front that has no pack file
5. Project directories and overviews created (if applicable)
6. `WELCOME-TO-BRAINIA.md` guide created, listing the core skills plus one block per active front
7. User understands next steps and where their profile is stored
8. **The user was never asked what they do for a living, and nothing was withheld based on their occupation**

## Error Handling

**If profile already exists:**
- Don't overwrite, offer update mode instead
- Preserve existing content, only append/modify requested sections
- Archive old version to `vault/00-inbox/archive/MY-PROFILE-YYYY-MM-DD.md` if starting fresh

**If directory creation fails:**
- Report which directories couldn't be created
- Provide manual creation instructions
- Continue with rest of setup

**If user exits mid-onboarding:**
- Create partial profile with note: "Onboarding incomplete - run onboarding skill to finish"
- Save what was collected so far
- Resume from last completed step on next run

## Privacy & Data

All configuration data is stored as markdown files in:
- `vault/00-inbox/MY-PROFILE.md` - Basic profile with active fronts
- `vault/00-inbox/MY-INTERESTS.md` - Interest areas
- `vault/00-inbox/MY-INTEGRATIONS.md` - Active/disabled external service integrations
- `vault/03-professional/COMPETITIVE-WATCHLIST.md` - Competitive tracking
- `vault/04-projects/[project]/PROJECT-OVERVIEW.md` - Project details

Benefits of markdown storage:
- Human-readable and editable
- Version controlled with Git
- Searchable in Obsidian
- Linkable from other notes
- No parsing required, just read as text
- Can be archived, moved, organized like any other note

## Philosophy

Brainia's configuration is **knowledge, not configuration**. By storing preferences as markdown notes:
- They're part of your knowledge base, not hidden config files
- You can link to them, reference them, evolve them
- They have context and can include your own notes
- They're transparent and auditable
- They benefit from all of Obsidian's features (tags, links, search, graph view)

This is "configuration as knowledge" - your preferences are themselves notes in your second brain.

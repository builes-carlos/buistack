# Brainia: Agentic Second Brain - Universal Agent Commands

This document defines the available commands/skills for AI agents interacting with Brainia, a self-evolving agentic second brain built on the COG engine (Cognition + Obsidian + Git).

**Compatible with:** OpenAI agents, Claude (via this file), and any AI that reads markdown.

> **Note:** Claude Code users should use `.claude/skills/` and Kiro users should use `.kiro/powers/` for native support. This file serves as universal documentation for all other agents.

## Available Commands

### /onboarding

**Description:** Personalize Brainia for your workflow - creates profile, interests, and watchlist files with a smart, conversational setup.

**Triggers:**
- `/onboarding`
- "onboarding"
- "setup Brainia"
- "setup my profile"
- "get started"

**Purpose:** Welcome new users and collect essential information to personalize their Brainia experience through natural conversation - not sequential form-filling. Creates profile documents stored as markdown files within the vault.

**How it works:**
1. Asks ONE open-ended question: "Tell me about yourself - name, role, and what you're interested in"
2. Intelligently parses the response to extract name, interests, projects, news sources, and competitive watchlist. Occupation is optional free text if volunteered, and it gates nothing
3. Only asks a follow-up if required info (name, interests) is still missing. **It never asks what the user does for a living**
4. Asks about agent mode preference (solo vs team) during confirmation
5. Confirms extracted info before creating files
6. Resolves fronts from the filesystem: matches the sibling folders next to `Brain/` against `front_id` and `aliases` in `fronts/*.md`. A sibling with no pack is still a front
7. Discovers integrations — presents whatever the active fronts declare, asks which tools the user already uses
8. Creates `vault/00-inbox/MY-PROFILE.md` with active_fronts, agent_mode, and preferences
9. Creates `vault/00-inbox/MY-INTERESTS.md` with topics for daily briefs
10. Creates `vault/00-inbox/MY-INTEGRATIONS.md` with active/disabled integrations
11. Optionally creates project structures in `vault/04-projects/` and `vault/03-professional/COMPETITIVE-WATCHLIST.md` (only if mentioned)
12. Generates a welcome guide with the core skills plus one block per active front

**Agent modes:**
- **Solo** (default): All skills handle everything directly in one conversation
- **Team**: Skills delegate research, analysis, and writing to specialist sub-agents for deeper results (works best with Claude Code)

**Design principle:** Never ask redundant questions. Never show numbered option menus. Infer what you can from context.

**Run this first** if you're new to Brainia.

---

### /braindump

**Description:** Quick capture of raw thoughts with intelligent domain classification and competitive intelligence extraction.

**Triggers:**
- `/braindump`
- "braindump"
- "brain dump"
- "capture thoughts"
- "write down ideas"
- "get thoughts out of my head"

**Purpose:** Transform raw thoughts into strategic intelligence through quick capture, systematic analysis, pattern recognition, and domain-aware insight extraction with minimal user friction.

**What it does:**
1. Accepts stream-of-consciousness input (any format)
2. Classifies content by domain (personal/professional/project-specific)
3. Extracts themes, questions, decisions, and action items
4. Generates strategic insights and pattern recognition
5. Auto-extracts competitive intelligence if watchlist exists
6. Saves structured output to appropriate domain folder

**Output locations:**
- Personal: `vault/02-personal/braindumps/`
- Professional: `vault/03-professional/braindumps/`
- Project: `vault/04-projects/[project-slug]/braindumps/`
- Mixed: `vault/00-inbox/`

---

### /daily-brief

**Description:** Generate personalized news intelligence with verified sources (7-day freshness requirement).

**Triggers:**
- `/daily-brief`
- "daily brief"
- "news"
- "what's happening"
- "morning brief"
- "daily news"

**Purpose:** Find verified, relevant news for personalized daily briefings with strict verification standards and strategic relevance analysis tailored to user's specific interests and projects.

**What it does:**
1. Reads user interests from `vault/00-inbox/MY-INTERESTS.md`
2. Searches for news within last 7 days only
3. Verifies sources with credibility assessment (Tier 1/2/3)
4. Analyzes strategic relevance to user's role and projects
5. Identifies opportunities and threats
6. Generates comprehensive briefing with sources

**Output location:** `vault/01-daily/briefs/daily-brief-YYYY-MM-DD.md`

**Key features:**
- All news must be from last 7 days (mandatory)
- Minimum 2 credible sources per claim
- Confidence levels explicitly stated
- Action items and recommendations included

---

### /weekly-checkin

**Description:** Cross-domain pattern analysis and strategic reflection for weekly review.

**Triggers:**
- `/weekly-checkin`
- "weekly checkin"
- "weekly check-in"
- "weekly review"
- "reflect on my week"
- "week reflection"

**Purpose:** Comprehensive weekly review and analysis integrating insights across all domains (personal, professional, projects) with pattern recognition and strategic planning.

**What it does:**
1. Scans recent braindumps, briefs, and check-ins
2. Guides user through reflection questions
3. Reviews each domain (personal, professional, projects)
4. Identifies patterns across the week
5. Helps set priorities for next week
6. Generates structured check-in document

**Output location:** `vault/01-daily/checkins/weekly-checkin-YYYY-MM-DD.md`

**Covers:**
- Overall week assessment and rating
- Personal wellness and growth
- Professional accomplishments
- Project progress for each active project
- Cross-domain patterns and insights
- Forward planning with priorities

---

### /knowledge-consolidation

**Description:** Build frameworks from scattered insights across all braindumps and notes.

**Triggers:**
- `/knowledge-consolidation`
- "consolidate knowledge"
- "build frameworks"
- "synthesize insights"
- "extract patterns"

**Purpose:** Transform scattered insights from braindumps, daily briefs, and check-ins into coherent frameworks and "single source of truth" knowledge documents through pattern recognition and systematic synthesis.

**What it does:**
1. Scans vault for unprocessed content (braindumps, briefs, check-ins)
2. Applies pattern recognition (frequency, temporal, domain correlation)
3. Identifies contradictions and cross-cutting patterns
4. Develops actionable frameworks from patterns
5. Updates existing frameworks or creates new ones
6. Generates consolidation report
7. Marks processed braindumps as consolidated

**Output locations:**
- Frameworks: `vault/05-knowledge/consolidated/[framework-name]-framework.md`
- Patterns: `vault/05-knowledge/patterns/pattern-[name].md`
- Timeline: `vault/05-knowledge/timeline/[topic]-evolution-YYYY-MM.md`
- Reports: `vault/05-knowledge/consolidated/consolidation-YYYY-MM-DD.md`

---

### /url-dump

**Description:** Quick capture URLs with automatic content extraction, insights, and categorization into knowledge booklets.

**Triggers:**
- `/url-dump`
- "url dump"
- "save this link"
- "bookmark this"
- "save for later"
- Pasting a URL

**Purpose:** Transform raw URLs into structured, insightful knowledge entries through intelligent content extraction, categorization, and integration with the user's knowledge base.

**What it does:**
1. Validates and fetches URL content
2. Extracts title, author, date, main content
3. Auto-categorizes (articles, tools, reference, research, etc.)
4. Generates summary and key insights
5. Assesses relevance to user interests/projects
6. Creates structured bookmark file

**Categories:**
- Articles & Blogs
- Tools & Resources
- Reference & Documentation
- Research & Papers
- Inspiration & Design
- Videos & Media
- News & Updates
- Project-Specific

**Output locations:**
- Standard: `vault/05-knowledge/booklets/[category]/[title-slug]-YYYY-MM-DD.md`
- Project-specific: `vault/04-projects/[project-slug]/resources/`
- Unclear: `vault/00-inbox/`

---

### /team-brief

> **Owned by the Work front, not the core.** Lives in `fronts/work/skills/` and is only available
> once the Work front is activated.

**Description:** Generate a daily team intelligence brief by cross-referencing Linear, Slack, GitHub, PostHog, meetings, and braindumps — then sync the resulting intelligence back into Linear.

**Triggers:**
- `/team-brief`
- "team brief"
- "what did we ship?"
- "daily team update"
- "summarize the team's progress"

**Purpose:** Build an evidence-backed operating brief for product and engineering leads by combining multiple sources of truth, highlighting blockers and momentum, and writing the most important updates back to Linear.

**What it does:**
1. Pulls active initiatives, projects, and issues from Linear
2. Cross-references GitHub PRs, Slack discussions, meetings, PostHog, and braindumps
3. Summarizes shipped work, in-progress work, risks, and signals that matter
4. Writes initiative status updates and issue/project sync-backs into Linear where appropriate
5. Produces a concise brief with a Linear sync report

**Output location:** `vault/03-professional/team-briefs/team-brief-YYYY-MM-DD.md`

---

### /meeting-transcript

**Description:** Process meeting transcripts into structured decisions, action items, and strategic themes.

**Triggers:**
- `/meeting-transcript`
- "process this meeting"
- "analyze this transcript"
- "summarize this meeting"
- "meeting notes from transcript"

**Purpose:** Turn noisy transcripts into clean decision records, action items, and key strategic signals without losing the substance of the conversation.

**What it does:**
1. Cleans transcript noise and identifies speakers/topics
2. Extracts decisions, action items, unresolved questions, and strategic themes
3. Highlights stakeholder concerns, alignment, and follow-up needs
4. Formats the result into a reusable meeting note

**Output location:** `vault/03-professional/meetings/meeting-transcript-YYYY-MM-DD-[slug].md`

---

### /comprehensive-analysis

**Description:** Run a deep 7-day product, team, and strategy analysis for weekly reviews, board prep, or planning.

**Triggers:**
- `/comprehensive-analysis`
- "weekly analysis"
- "board prep"
- "comprehensive analysis"
- "deep weekly review"

**Purpose:** Synthesize the last week across product, engineering, customer signals, and strategy into a single high-signal analysis for leaders.

**What it does:**
1. Reviews recent team briefs, meetings, project artifacts, and external signals
2. Identifies what shipped, what changed, what is blocked, and what needs leadership attention
3. Surfaces trends, risks, opportunities, and recommended actions
4. Produces an executive-ready synthesis with confidence levels and open questions

**Output location:** `vault/03-professional/analysis/comprehensive-analysis-YYYY-MM-DD.md`

---

### /scout

**Description:** Evaluate URLs and tools — check vault coverage, assess relevance, recommend save or skip.

**Triggers:**
- `/scout`
- "scout this"
- "evaluate this"
- "should I save this?"
- "is this relevant?"

**Purpose:** Lightweight triage that sits between "ignore" and `/url-dump`. Checks existing vault coverage, assesses relevance to your profile and interests, and recommends save or skip.

**What it does:**
1. Accepts URL(s) or tool name(s)
2. Searches the entire vault for existing coverage (duplicates, mentions)
3. If new — fetches content, detects type (tool, article, repo, research, news, reference)
4. Assesses relevance against your profile (projects, role, tech stack) and interests
5. Recommends **Save** (hands off to `/url-dump` with pre-filled category) or **Skip** (explains why)
6. Supports batch mode (multiple URLs in one invocation)

**Boundary with `/url-dump`:** Scout evaluates ("should I save this?"). URL-dump saves ("save this now"). If you already know you want to save, use `/url-dump` directly.

---

### /front-sync

**Description:** Distill the artifacts an active front declares in `reads_back` into vault notes, and correct any claim the source now contradicts.

**Triggers:**
- `/front-sync` (all active fronts) or `/front-sync <front_id>`
- "sync my fronts", "pull in my project state", "what changed in my projects"
- Before answering a question that depends on current front state when the last sync is stale

**What it does:**
1. Reads `active_fronts` from `vault/00-inbox/MY-PROFILE.md`
2. For each active front, reads its pack's `reads_back`, `sibling` and `writes_to` declarations. Filenames are never hardcoded; the pack is the contract
3. Locates the declared artifacts in the sibling folder, one set per unit of work (the software front has one per project)
4. Writes a **distilled** note per unit at `writes_to`, with a source citation and real date per factual claim
5. Diffs against the previous note and reports what is new, changed, **invalidated**, or merely stale. Invalidated claims are corrected in place
6. Reports missing artifacts instead of inferring them

**Hard boundaries:** read-only on the sibling folder; never copies a source artifact into the vault (see the reference-layer HARD RULE); never does the front's work. If a front's artifacts are stale, the fix is to run that front's methodology, not to have Brainia guess.

**Output location:** each front's declared `writes_to` (for the software front, `vault/04-projects/<project>/`)

---

### /update-brainia

**Description:** Check for and apply upstream COG framework updates without touching personal content.

**Triggers:**
- `/update-brainia`
- "update COG"
- "check for updates"
- "get latest COG version"
- "upgrade COG"
- "new COG version"

**Purpose:** Safely update framework files (skills, docs, scripts) from the official upstream repository while leaving all personal content untouched.

**What it does:**
1. Reads `BRAINIA-VERSION` to determine current version
2. Adds/fetches the `upstream` remote from the official repo
3. Compares each framework file against upstream
4. Detects customizations and offers per-file keep/overwrite/backup
5. Applies updates via surgical `git checkout` (no merge conflicts)
6. Reports updated files and suggests committing

**Shell script alternative:**
```bash
./brainia-update.sh           # Interactive
./brainia-update.sh --check   # Check for updates
./brainia-update.sh --dry-run # Preview changes
./brainia-update.sh --force   # Update all without prompting
```

**Safety:** Content folders (`vault/00-inbox/`, `vault/01-daily/`, `vault/02-personal/`, etc.) are NEVER touched. Only framework files (skills, docs, scripts) are updated.

---

### /auto-research

**Description:** Deep strategic research engine — decomposes questions into parallel research threads, spawns multiple agents, and synthesizes into actionable strategic analysis.

**Triggers:**
- `/auto-research`
- "research [topic]"
- "investigate [question]"
- "strategic analysis"
- "deep dive into [topic]"

**Purpose:** Take a high-level strategic question, decompose it into 5-7 parallel research threads, investigate each with real web sources, and synthesize findings into an actionable strategic analysis with scenarios and recommendations.

**What it does:**
1. Decomposes the question into independent research threads (market forces, historical precedent, player analysis, technology trajectory, emerging tech, contrarian view, etc.)
2. Presents decomposition for user approval before launching research
3. Spawns parallel research agents (team mode) or runs sequential research passes (solo mode)
4. Each thread searches 8-12 high-quality sources via web search
5. Synthesizes all threads into a unified strategic analysis with scenarios, options, and recommendations
6. Saves to vault with executive summary

**Output location:** `vault/05-knowledge/research/YYYY-MM-DD-[slug].md`

**Key features:**
- No hallucinated sources — every claim traces to real web search results
- Emerging tech thread always included — surfaces pre-mainstream concepts
- Contrarian view section challenges consensus
- Confidence levels and gaps explicitly stated

---

### PM Workflow Skills — owned by the Work front, not the core

> **These are not core commands.** They live in `fronts/work/skills/` and only exist in
> `.claude/skills/` once the Work front is activated. If the user has no Work front, do not
> offer them, do not mention them, and do not treat their absence as a broken install.
> See "Front Packs" for how activation works.

The following 6 skills form a complete product management lifecycle:
**Research** → **PRD** → **Stories** → Development → **Release Notes** → **Knowledge Base**

### /create-user-story

**Description:** Create user stories with duplicate checking across Linear, GitHub Issues, or Jira.

**Triggers:**
- `/create-user-story`
- "create a user story"
- "create a story for"
- "new user story"

**Purpose:** Create well-structured user stories in your project tracker with automatic duplicate detection, standard As a/I want/So that format, and Given/When/Then acceptance criteria.

**What it does:**
1. Accepts problem statement and solution from user
2. Checks active integrations (Linear, GitHub, Jira) in `vault/00-inbox/MY-INTEGRATIONS.md`
3. Searches for potential duplicate issues in the active tracker
4. If duplicates found, stops and shows candidates
5. If no duplicates, creates story with user story format and acceptance criteria
6. Saves a copy to `vault/04-projects/[project]/stories/`

**Output:** Issue created in active tracker + local copy in vault

---

### /generate-prd

**Description:** Draft product requirement documents with an approval gate before publishing.

**Triggers:**
- `/generate-prd`
- "generate a PRD"
- "draft PRD"
- "product requirements"

**Purpose:** Generate structured PRDs from problem context, save to vault, and optionally publish to Confluence/Notion with explicit human approval.

**What it does:**
1. Collects problem statement, goals, user context from user
2. Reads existing project context from `vault/04-projects/` and `vault/05-knowledge/`
3. Drafts PRD with standard sections (Problem, Goals, Non-goals, User workflows, Functional requirements, Iterations, Dependencies, Risks, Success metrics)
4. Saves to `vault/04-projects/[project]/PRDs/PRD-[slug].md`
5. Presents summary and asks for explicit approval before any publishing
6. Only publishes to Confluence/Notion if user explicitly approves

**Output location:** `vault/04-projects/[project]/PRDs/PRD-[slug].md`

---

### /generate-release-notes

**Description:** Generate release notes from GitHub milestones, Linear cycles, or manual input.

**Triggers:**
- `/generate-release-notes`
- "generate release notes"
- "release notes for"
- "what shipped in"

**Purpose:** Compile release notes by pulling completed issues/PRs from your tracker, categorizing into enhancements, improvements, and bug fixes.

**What it does:**
1. Identifies release scope (GitHub milestone, Linear cycle, or manual list)
2. Fetches all completed issues/PRs in the release
3. Categorizes into Enhancements, Technical Improvements, Bug Fixes
4. Generates formatted release notes markdown
5. Saves to `vault/04-projects/[project]/releases/`
6. Optionally publishes to Confluence with approval

**Output location:** `vault/04-projects/[project]/releases/release-notes-[version]-YYYY-MM-DD.md`

---

### /export-open-issues

**Description:** Audit and export open issues from any project tracker.

**Triggers:**
- `/export-open-issues`
- "export open issues"
- "issue audit"
- "open issues report"

**Purpose:** Generate a structured audit of all open issues from your active tracker for review, grooming, or stakeholder reporting.

**What it does:**
1. Checks active integrations for available trackers
2. Fetches all open issues with metadata (assignee, priority, labels, dates)
3. Generates summary statistics and categorized breakdown
4. Identifies stale issues, unassigned work, and priority imbalances
5. Saves structured report to vault

**Output location:** `vault/04-projects/[project]/audits/open-issues-YYYY-MM-DD.md`

---

### /publish-to-confluence

**Description:** Publish any vault markdown file to Confluence.

**Triggers:**
- `/publish-to-confluence`
- "publish to Confluence"
- "push to Confluence"

**Purpose:** Publish a local markdown file from the vault to a Confluence page (create or update), with explicit approval before publishing.

**What it does:**
1. Accepts path to local markdown file
2. Requires Confluence integration to be active
3. Converts markdown to Confluence-compatible format
4. Creates new page or updates existing page
5. Returns published page URL

**Requires:** Confluence integration active in `vault/00-inbox/MY-INTEGRATIONS.md`

---

### /update-knowledge-base

**Description:** Maintain product knowledge base from releases, features, and project changes.

**Triggers:**
- `/update-knowledge-base`
- "update knowledge base"
- "update KB"
- "sync knowledge base"

**Purpose:** Keep your product knowledge base in `vault/05-knowledge/` current by incorporating release data, feature updates, and project changes.

**What it does:**
1. Reads current knowledge base files from `vault/05-knowledge/`
2. Accepts feature updates and/or release version as input
3. Cross-references with project PRDs and release notes in `vault/04-projects/`
4. Updates knowledge base with factual, thorough changes
5. Optionally syncs to external wiki (Confluence/Notion) with approval

**Output location:** `vault/05-knowledge/consolidated/product-knowledge-base.md`

---

## Worker Agents

Brainia includes 6 specialized worker agents (`.claude/agents/`) that handle data-heavy tasks using Sonnet while the lead session (Opus) handles reasoning and synthesis. Inspired by [garrytan/gstack](https://github.com/garrytan/gstack) specialist sessions and [garrytan/gbrain](https://github.com/garrytan/gbrain) knowledge patterns.

| Agent | What it does | When it's used |
|---|---|---|
| **worker-data-collector** | Structured extraction from GitHub, Slack, Jira, Linear, or files | Team briefs, issue audits, data gathering |
| **worker-researcher** | Web research with source citations and evidence | Auto-research threads, daily brief sourcing |
| **worker-file-ops** | Vault reads/writes, metadata, profile updates | Knowledge consolidation, profile maintenance |
| **worker-executor** | Pre-approved mutations (Jira transitions, Linear updates) | Team brief sync-back, issue management |
| **worker-publisher** | Publishing to Slack, Confluence, Notion, webhooks | Brief publishing, wiki sync |
| **brief-people-updater** | Batch-update people profiles from meetings/briefs | After team briefs, meeting processing |

**Key rule:** Workers write results to `/tmp/{task-slug}.md` and return only a short status + file path. The lead session reads the file for synthesis.

---

## People CRM

Brainia tracks the people you work with using progressive, evidence-based profiles stored in `vault/05-knowledge/people/`.

**Profile structure:** Each person has a two-layer file:
1. **Compiled Truth** (top) — current best understanding, updated as evidence changes
2. **Timeline** (bottom) — append-only dated entries with source citations

**Tiered enrichment** — profiles auto-escalate:
- **Tier 3 (Stub):** 1 mention → name, role, one-line context
- **Tier 2 (Moderate):** 3+ mentions → executive snapshot, working style, strengths
- **Tier 1 (Full):** 8+ mentions or direct meeting → complete profile

**Citation format:** Every observation must include:
`[Source: [[path/to/source-note]] | YYYY-MM-DD | confidence: high|medium|low]`

Create profiles manually using the template at `06-templates/people-profile-template.md` or run the `brief-people-updater` agent for batch updates.

---

## Vault Structure

This repo is the `Brain/` of an `AI-Coached-Life` container — the cognition engine. `Brain/` is the only required folder besides the container root. Every life front is a physical sibling folder of `Brain/` (`Code/`, `Strategy/`, `Health/`, … — they vary per person); sources and artifacts live in the sibling, `.md` knowledge lives only in `Brain/vault/`. Inside `Brain/`:

```
AI-Coached-Life/Brain/
├── .claude/agents/        # Worker agent definitions (6)
├── fronts/                # Front packs, optional per front (+ front-owned skills and profiles)
├── vault/00-inbox/              # Landing zone, profile files
│   ├── MY-PROFILE.md      # User profile with role pack (created by onboarding)
│   ├── MY-INTERESTS.md    # User interests (created by onboarding)
│   └── MY-INTEGRATIONS.md # Active/disabled integrations (created by onboarding)
├── vault/01-daily/              # Daily content
│   ├── briefs/            # Daily intelligence briefs
│   └── checkins/          # Weekly check-ins
├── vault/02-personal/           # Personal domain
│   └── braindumps/        # Personal braindumps
├── vault/03-professional/       # Professional domain
│   ├── braindumps/        # Work-related braindumps
│   └── COMPETITIVE-WATCHLIST.md
├── vault/04-projects/           # Project-specific content
│   └── [project-slug]/
│       ├── PROJECT-OVERVIEW.md
│       ├── braindumps/
│       ├── competitive/
│       └── resources/
├── vault/05-knowledge/          # Consolidated knowledge
│   ├── consolidated/      # Frameworks and reports
│   ├── patterns/          # Identified patterns
│   ├── people/            # People CRM profiles
│   ├── timeline/          # Thinking evolution
│   └── booklets/          # URL bookmarks by category
└── 06-templates/          # Document templates (incl. people profile)
```

---

## Quick Start

1. **New user?** Run `/onboarding` first to set up your profile
2. **Capture thoughts?** Use `/braindump` anytime
3. **Morning routine?** Run `/daily-brief` for your intelligence briefing
4. **End of week?** Use `/weekly-checkin` to reflect
5. **Save a link?** Use `/url-dump` with the URL
6. **Evaluate a tool?** Use `/scout` to check relevance before saving
7. **Build knowledge?** Run `/knowledge-consolidation` periodically
8. **Process a meeting?** Use `/meeting-transcript` with the recording
9. **Deep review?** Use `/comprehensive-analysis` for a 7-day pass
10. **Strategic research?** Use `/auto-research` with your question
11. **Project state gone stale?** Run `/front-sync` to pull each front's own artifacts back in

Those are the core commands and they work for everyone. Anything beyond them belongs to a front:

- **Writing code?** The software front hands off to devaing. Start with `/devaing-director`. Brainia does not build software itself.
- **PM and delivery work?** Activate the Work front for `/create-user-story`, `/generate-prd`, `/generate-release-notes`, `/export-open-issues`, `/publish-to-confluence`, `/update-knowledge-base` and `/team-brief`.
- **Anything else?** Declare it in a front pack. See `fronts/_template.md`.

---

## Configuration

All configuration is stored as readable markdown files:
- `vault/00-inbox/MY-PROFILE.md` - Profile, role pack, agent mode, and active projects
- `vault/00-inbox/MY-INTERESTS.md` - Topics for news curation
- `vault/00-inbox/MY-INTEGRATIONS.md` - Active/disabled external service integrations
- `vault/03-professional/COMPETITIVE-WATCHLIST.md` - Companies/people to track

Edit these files anytime - changes take effect immediately.

### Front Packs

Brainia personalizes by **front**, never by job title. It never asks what the user does for a living, and it never gives less to someone whose work is not software.

Fronts are detected from the filesystem: the sibling folders next to `Brain/`. A front pack (`fronts/<id>.md`) is optional and declares:
- `writes_to` — which vault paths this front's knowledge lands in
- `skills` — front-owned skills under `fronts/<id>/skills/`, copied into `.claude/skills/` only on activation
- `methodology` — an external tool this front delegates execution to, plus how to detect it
- `reads_back` — artifacts Brainia ingests from the sibling folder
- `profiles` — optional sub-profiles for recommendation ordering inside that front

**The filesystem is the source of truth, not `fronts/`.** A sibling folder is a front whether or not a pack exists for it, and a front with no pack is never "unconfigured". The set is open and changes over time.

Two packs ship with content: `fronts/code.md` delegates to **devaing** (<https://github.com/builes-carlos/devaing>) and reads each project's `CONTEXT.md` and `CHECKPOINTS.md` back into `vault/04-projects/`; `fronts/work.md` owns the seven PM and delivery skills. Write your own from `fronts/_template.md`, and front-local profiles from `fronts/_profile-template.md`.

## Version & Updates

COG tracks its version in `BRAINIA-VERSION` (currently 4.0.0). To check for updates:
- Run `/update-brainia` in any supported agent
- Or use the shell script: `./brainia-update.sh --check`
- Validate packaged agent surfaces with `./scripts/validate-agent-surface.sh`

Updates only touch framework files (skills, docs, scripts) — your personal content is never modified.

---

## Task Format

All skills generate tasks with [Obsidian Tasks emoji format](https://publish.obsidian.md/tasks/Reference/Task+Formats/Tasks+Emoji+Format) for dashboard compatibility:

```markdown
- [ ] Action item 📅 YYYY-MM-DD
```

**Date calculation by context:**
- "Immediate (24-48 hours)" → tomorrow's date
- "Short-term (1-2 weeks)" → +1 week from today
- "Today/This Week" → today or end of week
- "Next Steps" → next Monday/Friday

This enables:
- Tasks dashboard queries ("due today", "due this week")
- Daily notes task views
- Date-based filtering and sorting

---

## Philosophy

Brainia follows these principles:
- **Verification-first:** All information sourced and verified
- **Transparency:** Confidence levels explicitly stated
- **Configuration as knowledge:** Preferences stored as editable notes
- **Self-evolving:** Patterns and frameworks grow over time
- **Low friction:** Quick capture, systematic organization
- **Obsidian Tasks compatible:** All tasks include emoji due dates

# Skill: Export KB

**Purpose:** Generate optimized export files for Claude Project Knowledge, consolidating the campaign KB into files suitable for uploading to a Claude Project.

**Input:** The KB content (`grimwild-kb/` directory) and GM notes (`gm-notes/` directory)

**Output:** Files in `exports/` directory

---

## Workflow

### Step 1 — Scan KB state

Read all content from the KB directories to build a complete picture:

| Directory | Content |
|-----------|---------|
| `grimwild-kb/pcs/` | Player character files |
| `grimwild-kb/npcs/` | NPC files |
| `grimwild-kb/locations/` | Location files |
| `grimwild-kb/items/` | Item files |
| `grimwild-kb/factions/` | Faction files |
| `grimwild-kb/world/` | World setting files |
| `grimwild-kb/sessions/` | Session summaries |
| `grimwild-kb/story-arcs/group/` | Group story arcs |
| `grimwild-kb/story-arcs/character/*/` | Character story arcs |
| `gm-notes/` | GM secrets and planning notes |

Build an entity index mapping canonical names to file paths for cross-reference resolution.

### Step 2 — Ensure exports directory exists

Create `exports/` directory if it doesn't exist.

### Step 3 — Generate campaign-index.md

Create `exports/campaign-index.md` containing:

```markdown
# [Campaign Name] - Campaign Index

## Campaign Overview
[2-3 paragraph description of the campaign premise and current state]

## Player Characters

### [Character Name]
**Player:** [Player (Discord name)]
**Concept:** [Full concept paragraph from PC file]
**Key Abilities:** [Notable talents/backgrounds]
**Relationships:** [Brief list of key relationships to other PCs]
**Current Threads:** [Active personal plot hooks]

[Repeat for each PC]

## Active Story Arcs

### Group: [Arc Name]
**Theme:** [Arc theme]
**Status:** [Current phase/status]

[Full summary paragraph from arc file]

**Open Questions:**
- [List key open questions from arc file]

### Character: [Character] - [Arc Name]
**Theme:** [Arc theme]
**Status:** [Current phase]

[Summary and current state]

**Open Questions:**
- [Character-specific open questions]

[Repeat for each character arc]
```

**Notes for Step 3:**
- For PCs: Pull concept, key abilities, relationships, and current threads from the PC file
- For Story Arcs: Include full summary and open questions list from the arc file
- Keep narrative voice consistent with KB conventions (no game mechanics meta-references)
- Do NOT include an "Export Files" section (RAG will handle finding other files)

### Step 4 — Generate characters-pcs.md

Consolidate all files from `grimwild-kb/pcs/*.md`:

- Add a header: `# Player Characters`
- For each PC file, include full content with a level-2 header for navigation
- Preserve all frontmatter, relationships, and cross-references
- Order alphabetically by character name

### Step 5 — Generate characters-npcs.md

Consolidate all files from `grimwild-kb/npcs/*.md`:

- Add a header: `# Non-Player Characters`
- For each NPC file, include full content with a level-2 header
- Preserve relationships, affiliations, and cross-references
- Order alphabetically by character name

### Step 6 — Generate locations.md

Consolidate all files from `grimwild-kb/locations/*.md`:

- Add a header: `# Locations`
- Group by region or type if the files indicate such structure
- For each location, include full content with appropriate header level
- Preserve geographic relationships and cross-references

### Step 7 — Generate world-setting.md

Consolidate content from multiple sources:

- Add a header: `# World Setting`
- Include all files from `grimwild-kb/world/*.md`
- Include all files from `grimwild-kb/factions/*.md` under a `## Factions` section
- Include all files from `grimwild-kb/items/*.md` under a `## Notable Items` section
- Preserve lore, history, and cross-references

### Step 8 — Generate story-arcs-active.md

Consolidate active story arcs:

- Add a header: `# Active Story Arcs`
- Include group arcs from `grimwild-kb/story-arcs/group/*.md` (exclude `hooks.md`)
- Include character arcs from `grimwild-kb/story-arcs/character/*/*.md` (exclude `hooks.md`)
- Filter to active arcs only (check status in frontmatter or content)
- Organize by scope: Group arcs first, then character arcs grouped by character

### Step 9 — Generate sessions-recent.md

Include recent session summaries:

- Add a header: `# Recent Sessions`
- Include the last 3-5 sessions from `grimwild-kb/sessions/`
- Order by session number (most recent first)
- Include full session content with cross-references
- If fewer than 3 sessions exist, include all available

### Step 10 — Generate hooks-all.md

Consolidate all hooks for brainstorming:

- Add a header: `# Story Hooks`
- Add introduction explaining these are open threads for future sessions
- Include `## Group Hooks` section with content from `grimwild-kb/story-arcs/group/hooks.md`
- Include `## Character Hooks` section with subsections for each character:
  - `### [Character Name]` with content from `grimwild-kb/story-arcs/character/[slug]/hooks.md`
- Preserve source session references and related entities for each hook

### Step 11 — Generate gm-notes.md

Consolidate GM-only content:

- Add a header: `# GM Notes`
- Add a prominent warning: `> **GM ONLY** - This file contains secrets and planning material not for player eyes.`
- Include all files from `gm-notes/*.md`
- Organize by file with level-2 headers
- Preserve all secrets, planned revelations, and NPC motivations

### Step 12 — Report generation summary

After all files are generated, report:

```
## Export Complete

**Files generated:**
| File | Size | Entries |
|------|------|---------|
| campaign-index.md | X KB | - |
| characters-pcs.md | X KB | N PCs |
| characters-npcs.md | X KB | N NPCs |
| locations.md | X KB | N locations |
| world-setting.md | X KB | N world + N factions + N items |
| story-arcs-active.md | X KB | N arcs |
| sessions-recent.md | X KB | N sessions |
| hooks-all.md | X KB | N group + N character hooks |
| gm-notes.md | X KB | N files |

**Total export size:** X KB

**Notes:**
- [Any issues, missing content, or warnings]

**Next steps:**
- Review generated files in `exports/`
- Upload to Claude Project Knowledge as needed
- Note: `gm-notes.md` contains spoilers - handle separately
```

---

## File Format Guidelines

### Headers
- Each export file starts with a level-1 header describing its contents
- Individual entries use level-2 headers for easy navigation
- Sub-sections use level-3 headers

### Cross-References
- Preserve entity references as they appear in source files
- Do not attempt to create hyperlinks between export files
- References will be resolved by Claude when reading the files together

### Frontmatter
- Strip YAML frontmatter from consolidated files (it's for KB tooling, not Claude)
- Preserve the information inline where relevant (status, relationships, etc.)

### Whitespace
- Two blank lines between major sections
- One blank line between entries within a section
- Consistent formatting throughout

---

## Exclusions

The following are NOT included in exports:

- `inbox/` - Working files, not finalized KB content
- `review/` - Process files for human review
- `config/` - Tooling configuration, not campaign content
- `templates/` - Empty templates
- Resolved/completed story arcs (unless recently concluded)

---

## Usage Notes

**When to run:**
- Before starting a new Claude Project conversation
- After significant KB updates (new sessions, major changes)
- When preparing for a planning/brainstorming session

**Upload strategy for Claude Projects:**
- Upload `campaign-index.md` first (gives Claude overview)
- Upload entity files as needed for the conversation topic
- Upload `hooks-all.md` when brainstorming future sessions
- Upload `gm-notes.md` only for GM-facing planning sessions

**File sizes:**
- Claude Project Knowledge has file size limits
- If any export exceeds reasonable size, consider splitting
- The skill will warn about unusually large files

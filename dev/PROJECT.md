# Grimwild KB - Development Instructions

**Purpose:** This file guides Claude Code during development of the Grimwild campaign knowledge base system.

---

## Project Overview

Build a campaign knowledge base system for a Grimwild TTRPG campaign. The system:
1. Processes Discord voice channel transcripts into clean, attributed text
2. Filters out non-game-related chatter (marks sections for human review)
3. Incorporates transcript content and planning notes into a structured markdown KB
4. Exports the KB in a format optimized for Claude Project Knowledge
5. Uses git for version control and human review of all changes

**Key principle:** Semi-automated with human-in-the-loop. The system proposes changes; Joe reviews via git diff and approves.

**Bootstrap approach:** Session Zero has notes but no transcript. Start by incorporating Session Zero notes to establish the initial KB (PCs, world basics, story setup). Session One transcript then builds on this foundation.

---

## Directory Structure

```
grimwild/                            (repo root)
├── config/
│   ├── speaker-map.yaml             # Discord names → Player/Character + transcription fixes
│   └── entity-aliases.yaml          # Alternative spellings → canonical entity names
│
├── grimwild-kb/                     # KB content
│   ├── sessions/
│   ├── story-arcs/
│   │   ├── group/
│   │   └── character/
│   ├── pcs/
│   ├── npcs/
│   ├── locations/
│   ├── items/
│   ├── factions/
│   └── world/
│
├── gm-notes/                        # Private, excluded from player-facing exports
│
├── inbox/
│   ├── transcripts/
│   │   ├── raw/                     # Untouched Discord downloads
│   │   ├── processed/               # After speaker mapping + transcription fixes
│   │   └── filtered/                # After non-game marking + human review (final)
│   └── notes/                       # Planning notes to incorporate
│
├── review/
│   └── pending-changes.md           # Conflicts/questions for human review
│
├── exports/
│
├── scripts/
│   └── download_transcript.py       # EXISTS - needs modification
│
├── skills/
│   ├── filter-transcript/
│   │   └── SKILL.md
│   ├── incorporate-session/
│   │   └── SKILL.md
│   ├── incorporate-notes/
│   │   └── SKILL.md
│   └── export-kb/
│       └── SKILL.md
│
├── templates/
│   ├── session.md
│   ├── pc.md
│   ├── npc.md
│   ├── location.md
│   ├── item.md
│   ├── faction.md
│   ├── story-arc.md
│   └── world-entry.md
│
├── dev/
│   └── PROJECT.md
│
└── CLAUDE.md                        # (Create at end of development, not now)
```

---

## Component Specifications

### 1. Config: `config/speaker-map.yaml`

```yaml
# Maps Discord usernames to players/characters and fixes common transcription errors

players:
  joe:
    role: gm
    display: "GM"
    discord_names:
      - "Killjoy Keegan"
    
  ramsey:
    role: player
    discord_names:
      - "feklars"
    characters:
      - name: "Sir Roderic Lightbearer"
        display: "Roderic"
        active: true
        sessions: "0-"
      
  ken:
    role: player
    discord_names:
      - "SiliKen"
    characters:
      - name: "Edric Bloom"
        display: "Edric"
        active: true
        sessions: "0-"
      
  dustin:
    role: player
    discord_names:
      - "duskit"
    characters:
      - name: "Castor"
        display: "Castor"
        active: true
        sessions: "0-"
      
  jay:
    role: player
    discord_names:
      - "regular human faits"
    characters:
      - name: "Garland yn Greenholt"
        display: "Garland"
        active: true
        sessions: "0-"

# Transcription corrections - case-insensitive replacements
# Add new entries as you discover speech-to-text errors
transcription_corrections:
  # Character name mishearings
  - match: "Roderick"
    replace: "Roderic"
  - match: "kather"
    replace: "Castor"
  - match: "Katherine"
    replace: "Castor"
  - match: "Castro"
    replace: "Castor"
  - match: "Garlin"
    replace: "Garland"
  - match: "Edrick"
    replace: "Edric"
  
  # Add location/term corrections as discovered
  # - match: "grim wild"
  #   replace: "Grimwild"
```

### 2. Config: `config/entity-aliases.yaml`

```yaml
# Maps alternative names/spellings to canonical entity filenames
# Used during KB incorporation to find existing entries

characters:
  "Sir Roderic": "sir-roderic-lightbearer"
  "Roderic": "sir-roderic-lightbearer"
  "the paladin": "sir-roderic-lightbearer"
  "Garland": "garland-yn-greenholt"
  "the wizard": "garland-yn-greenholt"
  "old man": "garland-yn-greenholt"
  # Add as entities accumulate

locations:
  "Ashen Vale": "ashen-vale"
  "the Vale": "ashen-vale"
  # etc.

# items:
# factions:
# npcs:
```

### 3. Script: `scripts/download_transcript.py` (MODIFY EXISTING)

**Changes needed:**
- Remove any processing/formatting currently being done
- Output should be raw, unmodified transcript
- Default output path: `inbox/transcripts/raw/session-{date}-raw.txt`
- Keep existing `--after`, `--before`, `--output`, `--input` flags

**Behavior:**
- Downloads transcript from Discord voice channel
- Saves exactly as received (raw)
- If `--input` provided, just copies to raw folder (for reprocessing old transcripts)

### 4. Script: `scripts/process_transcript.py` (NEW)

**Usage:**
```
process_transcript.py --input PATH [--output PATH] [--session NUMBER] [--config PATH]
```

**Arguments:**
- `--input`: Path to raw transcript (required)
- `--output`: Output path (default: `inbox/transcripts/processed/{input_basename}-processed.txt`)
- `--session`: Session number for character lookup (default: latest, for multi-character players)
- `--config`: Path to speaker-map.yaml (default: `config/speaker-map.yaml`)

**Behavior:**
1. Load speaker-map.yaml
2. For each line matching `[TIMESTAMP] SPEAKER: TEXT`:
   - Look up SPEAKER in discord_names across all players
   - Replace with character display name (or "GM")
   - If player has multiple characters, use session number to determine which
3. Apply all transcription_corrections to the full text (case-insensitive)
4. Write to output path
5. Print summary: lines processed, speakers found, corrections applied

**Edge cases:**
- Unknown speaker: Keep original name, print warning
- Speaker not in any discord_names: Keep original, warn

### 5. Skill: `skills/filter-transcript/SKILL.md`

**Purpose:** Mark non-game-related sections in a processed transcript for human review.

**Input:** A processed transcript file from `inbox/transcripts/processed/`

**Output:** Same transcript with HTML comments marking non-game sections, saved to `inbox/transcripts/filtered/`

**Marking format:**
```
[timestamp] GM: I'm going to go get some water.

<!-- NON-GAME SECTION: break/chit-chat -->
[timestamp] Edric: While he's gone...
[timestamp] Castor: Yeah that ice machine thing...
...
<!-- END NON-GAME SECTION -->

[timestamp] GM: Okay, so where were we...
```

**What counts as NON-GAME:**
- Real-world chit-chat (ice machines, personal anecdotes unrelated to game)
- AFK announcements and waiting chatter
- Technical issues (Discord problems, audio issues)
- Scheduling discussion

**What is GAME-RELATED (do NOT mark):**
- In-character dialogue and narration
- Rules discussions and clarifications
- Character ability discussions
- World-building discussion
- Dice roll announcements and results
- Session planning within the game context
- Jokes/banter that reference game content

**Instructions for the skill:**
1. Read the transcript
2. Identify contiguous blocks of non-game chatter
3. Wrap each block in the comment markers with a brief description
4. Preserve all content (human will delete after review)
5. When uncertain, do NOT mark - err toward keeping content
6. Report: number of sections marked, total lines marked

### 6. Skill: `skills/incorporate-session/SKILL.md`

**Purpose:** Analyze a filtered transcript and propose KB updates.

**Input:** 
- A final/filtered transcript from `inbox/transcripts/filtered/`
- Session number
- Optional: recap-teaser text

**Process:**
1. Read existing KB state (sessions/, pcs/, npcs/, locations/, etc.)
2. Read `config/entity-aliases.yaml` to resolve entity references
3. Analyze transcript for:
   - Major events and plot developments
   - New entities (NPCs, locations, items, factions)
   - Updates to existing entities
   - Story arc progress (new questions, answered questions)
   - Notable quotes
4. Generate proposed changes:
   - New session file from template
   - New entity files as needed
   - Updates to existing files
   - Story arc updates
5. For any conflicts or uncertainties, add to `review/pending-changes.md`

**Entity Alias Handling:**
- When creating a new entity, propose obvious aliases to add to `entity-aliases.yaml`:
  - Name variants (full name, short name, title + name)
  - Obvious descriptors if contextually clear ("the paladin" for Sir Roderic)
- When encountering a reference that can't be resolved via existing aliases, flag in `review/pending-changes.md`:
  ```markdown
  ## Unresolved References
  - Session 1, line 247: "the old wizard" - Add alias to Garland?
  - Session 1, line 312: "the beaver man" - Add alias to Castor?
  ```
- Never auto-add to entity-aliases.yaml—all additions appear in git diff for human approval

**Output:**
- Creates/modifies files in the KB (including proposed additions to entity-aliases.yaml)
- All changes visible via `git diff`
- Human reviews and commits

**Linking convention:**
- Use `[[Entity Name]]` wiki-style links in markdown
- These map to entity files via entity-aliases.yaml

### 7. Skill: `skills/incorporate-notes/SKILL.md`

**Purpose:** Incorporate planning notes (from Claude Mobile sessions) into KB.

**Input:** A markdown file from `inbox/notes/`

**Process:**
1. Read existing KB state (all entity directories)
2. Read `config/entity-aliases.yaml` to resolve entity references
3. Analyze note content
4. Determine what type of content it is:
   - Session prep → gm-notes/
   - World building → world/ or appropriate entity files
   - Character development → update PC/NPC files
   - Story arc planning → story-arcs/ + possibly gm-notes/ for secrets
5. Propose file creation/updates
6. Flag anything that contradicts existing KB for review

**Entity Alias Handling:**
- When creating a new entity, propose obvious aliases to add to `entity-aliases.yaml`:
  - Name variants (full name, short name, title + name)
  - Obvious descriptors if contextually clear
- When encountering a reference that can't be resolved via existing aliases, flag in `review/pending-changes.md`:
  ```markdown
  ## Unresolved References
  - inbox/notes/session-zero-prep.md: "the Shepherd's Teeth" - New entity? Or alias for existing?
  ```
- Never auto-add to entity-aliases.yaml—all additions appear in git diff for human approval

**Output:**
- Creates/modifies files in the KB (including proposed additions to entity-aliases.yaml)
- All changes visible via `git diff`
- Human reviews and commits

### 8. Skill: `skills/export-kb/SKILL.md`

**Purpose:** Generate optimized export for Claude Project Knowledge.

**Input:** The KB content (grimwild-kb/ directory)

**Output:** Files in `exports/` directory

**Export strategy:**
1. Generate `exports/campaign-index.md`:
   - Campaign overview
   - Quick reference for all PCs
   - List of active story arcs with status
   - Table of contents for all categories
   
2. Generate category summary files:
   - `exports/characters-pcs.md` - All PCs consolidated
   - `exports/characters-npcs.md` - All NPCs consolidated  
   - `exports/locations.md` - All locations
   - `exports/world-setting.md` - World entries consolidated
   - `exports/story-arcs-active.md` - Active arcs with current state
   - `exports/sessions-recent.md` - Last 3-5 session summaries
   
3. Each export file should be self-contained and include relevant cross-references

**Exclusions:**
- `gm-notes/` - Never export (private)
- `inbox/` - Working files, not KB content
- `review/` - Process files, not KB content
- Resolved story arcs older than X sessions (configurable)

---

## Templates

### `templates/session.md`

```markdown
# Session [NUMBER]: [TITLE]

**Date Played:** [DATE]
**In-Game Timeline:** [IF TRACKED]

## Recap-Teaser
> [The teaser read at session start]

## Summary
[2-3 paragraph narrative of what happened]

## Major Events
- [Event 1]
- [Event 2]

## New Questions & Hooks
- [Question or hook introduced]

## Questions Answered / Arcs Advanced
- [Resolution or progress]

## NPCs Introduced
- [[NPC Name]] - [Brief description]

## Locations Visited
- [[Location Name]]

## Notable Quotes
> [Memorable lines]

## Session Notes
[GM observations, pacing notes, things to revisit]
```

### `templates/pc.md`

```markdown
# [CHARACTER NAME]

**Player:** [PLAYER NAME]
**Status:** Active | Deceased | Retired

## Concept
[Brief character concept]

## Background
[Character backstory]

## Key Traits & Abilities
[Notable capabilities, talents, gear]

## Relationships
- [[Entity]] - [Relationship description]

## Current Threads
- [Active personal storylines]

## Session Appearances
- [[Session X]] - [Brief note]
```

### `templates/npc.md`

```markdown
# [NPC NAME]

**First Appeared:** [[Session X]]
**Status:** Active | Deceased | Unknown
**Affiliation:** [[Faction]] or Independent

## Description
[Physical description and demeanor]

## Role
[Their role in the story/world]

## Relationships
- [[Entity]] - [Relationship]

## Key Events
- [[Session X]] - [What happened]

## Notes
[GM notes visible to players]
```

### `templates/location.md`

```markdown
# [LOCATION NAME]

**Type:** City | Town | Wilderness | Building | Region
**First Visited:** [[Session X]]

## Description
[What the place looks like, feels like]

## Notable Features
- [Feature 1]
- [Feature 2]

## Connected Locations
- [[Location]] - [Relationship/direction]

## Associated NPCs
- [[NPC Name]] - [Their connection to this place]

## Events Here
- [[Session X]] - [What happened]

## Notes
[Additional details]
```

### `templates/item.md`

```markdown
# [ITEM NAME]

**Type:** Weapon | Artifact | Document | Misc
**Current Holder:** [[Character]] or Unknown
**First Appeared:** [[Session X]]

## Description
[What it looks like]

## Properties
[What it does, mechanical or narrative]

## History
[Known history of the item]

## Notes
[Additional details]
```

### `templates/faction.md`

```markdown
# [FACTION NAME]

**Type:** Organization | Religion | Nation | Group
**Status:** Active | Defunct | Unknown

## Overview
[What the faction is and what they want]

## Notable Members
- [[NPC Name]] - [Role]

## Relationships
- [[Faction/Entity]] - [Relationship]

## Associated Locations
- [[Location]] - [Connection]

## History with Party
- [[Session X]] - [Interaction]

## Notes
[Additional details]
```

### `templates/story-arc.md`

```markdown
# [ARC NAME]

**Type:** Group | Character ([CHARACTER NAME])
**Theme:** [e.g., "Make Things Right", "Discover the Truth"]
**Status:** Active | Resolved | Abandoned
**Started:** [[Session X]]
**Resolved:** [[Session Y]] (if applicable)

## Summary
[What this arc is about]

## Open Questions
- [Unanswered question 1]
- [Unanswered question 2]

## Answered Questions
- [Question] → [Answer] ([[Session X]])

## Key Events
- [[Session X]] - [Development]

## Related Entities
- [[Entity]] - [Connection to arc]

## GM Notes
[Notes - will be in gm-notes/ for secrets, here for player-visible]
```

### `templates/world-entry.md`

```markdown
# [TOPIC NAME]

**Category:** Gods | History | Races | Magic | Culture | Geography

## Overview
[General description]

## Details
[Specific information]

## Related Entries
- [[Entry]] - [Connection]

## Sources
- [[Session X]] - [How this was established/revealed]

## Notes
[Additional details]
```

---

## Development Tasks

### Phase 1: Foundation ✅
- [x] Create directory structure
- [x] Create config/speaker-map.yaml
- [x] Create config/entity-aliases.yaml (initial version)
- [x] Create all template files
- [x] Create review/pending-changes.md (initial version)

### Phase 2: Notes Incorporation (Session Zero)
- [x] Create skills/incorporate-notes/SKILL.md
- [ ] Test with Session Zero notes
- [ ] Populate initial KB: PCs, world basics, starting situation
- [ ] Refine skill based on output quality

### Phase 3: Transcript Processing
- [ ] Modify scripts/download_transcript.py (raw only)
- [ ] Create scripts/process_transcript.py
- [ ] Test with Session One raw transcript
- [ ] Adjust transcription_corrections as needed

### Phase 4: Transcript Filtering & Session Incorporation
- [ ] Create skills/filter-transcript/SKILL.md
- [ ] Create skills/incorporate-session/SKILL.md
- [ ] Test full pipeline with Session One transcript
- [ ] Refine skills based on output quality

### Phase 5: Export
- [ ] Create skills/export-kb/SKILL.md
- [ ] Generate initial export for Project Knowledge
- [ ] Verify export works well with Claude searches

### Phase 6: Documentation
- [ ] Create final CLAUDE.md for production use
- [ ] Document workflow for Joe
- [ ] Clean up/remove development files

---

## Testing Checklist

**Notes Incorporation (Session Zero as bootstrap):**
- [ ] Session Zero notes parsed correctly
- [ ] PC files created with correct content
- [ ] World/setting entries created
- [ ] Story arcs initialized
- [ ] Wiki-style links used consistently
- [ ] This becomes the foundation Session One builds on

**Transcript Processing:**
- [ ] Raw transcript downloads to correct location
- [ ] Speaker names correctly mapped to character names
- [ ] Transcription corrections applied (Roderick → Roderic, etc.)
- [ ] Unknown speakers generate warnings but don't fail

**Filtering:**
- [ ] Non-game sections correctly identified
- [ ] Game-related OOC (rules discussion) NOT marked
- [ ] Marking format is correct for easy manual editing
- [ ] Edge cases handled (uncertain → don't mark)

**Session Incorporation:**
- [ ] Session summary generated from template
- [ ] New entities detected and created
- [ ] Existing entities updated (not duplicated)
- [ ] Wiki-style links used consistently
- [ ] Conflicts flagged in pending-changes.md

**Export:**
- [ ] All expected export files generated
- [ ] gm-notes/ excluded from export
- [ ] Cross-references intact
- [ ] Files are self-contained and searchable

---

## Notes for Claude Code

1. **Always ask before creating/modifying files** - This is Joe's campaign data
2. **Use git diff liberally** - Show what will change before committing
3. **When uncertain, add to pending-changes.md** - Don't guess on conflicts
4. **Preserve existing content** - Updates should add, not replace unless explicitly told
5. **Test incrementally** - Don't try to build everything at once
6. **Reference this file** - These specs are the source of truth during development

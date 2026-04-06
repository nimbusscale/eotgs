# Skill: Export KB

**Purpose:** Generate optimized export files for Claude Project Knowledge, consolidating the campaign KB into files suitable for uploading to a Claude Project.

**Output:** Files in `exports/` directory

---

## Workflow

### Step 1 — Generate mechanical exports

Run the export script to produce the 8 mechanical files:

```bash
python3 scripts/export_kb.py
```

This generates: `characters-pcs.md`, `characters-npcs.md`, `locations.md`, `world-setting.md`, `story-arcs-active.md`, `sessions-recent.md`, `hooks-all.md`, `gm-notes.md`.

Review the summary table it prints.

### Step 2 — Read source material for campaign index

Read the following files to synthesize `campaign-index.md`:

- All PC files from `kb/pcs/`
- All active story arc files from `kb/story-arcs/group/` and `kb/story-arcs/character/*/` (exclude `hooks.md` files; filter to **Status:** Active)
- The last 2 session summaries from `kb/sessions/`

### Step 3 — Generate campaign-index.md

Write `exports/campaign-index.md` following this structure:

```markdown
# Echoes of the Godstorm - Campaign Index

## Campaign Overview
[2-3 paragraph synthesis of the campaign premise and current state]

## Player Characters

### [Character Name]
**Player:** [Player (Discord name)]
**Concept:** [Concept paragraph from PC file]
**Key Abilities:** [Notable talents/backgrounds from PC file]
**Relationships:** [Key relationships to other PCs]
**Current Threads:** [Active personal hooks from the PC's ## Hooks section, semicolon-separated]

[Repeat for each PC]

## Active Story Arcs

### Group: [Arc Name]
**Theme:** [Theme]
**Status:** [Status]

[Full summary paragraph from arc file]

**Open Questions:**
- [Open questions from arc file]

### Character: [Character Name] - [Arc Name]
**Theme:** [Theme]
**Status:** [Status]

[Summary and current state from arc file]

**Open Questions:**
- [Character-specific open questions]
```

**Guidelines:**
- Pull concept, key abilities, relationships, and hooks from the PC files
- Include full summary and open questions from active story arc files
- Keep narrative voice consistent — never reference "the session", "the GM", or game mechanics meta
- One sentence per line for all narrative prose
- Do NOT include an "Export Files" section (RAG handles finding other files)

### Step 4 — Publish website

Build and deploy the KB as a searchable website:

```bash
bash scripts/publish_site.sh
```

### Step 5 — Report summary

After all files are generated, report the complete summary:
- Include the summary table from Step 1
- Add campaign-index.md with its size
- Note total export size and any issues
- Include the website URL from the publish step

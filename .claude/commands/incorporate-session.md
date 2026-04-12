# Skill: Incorporate Session

**Purpose:** Process an extracted session YAML from `inbox/transcripts/extracted/` into the campaign knowledge base — creating a session file, updating entities, tracking story arcs, and extracting hooks.

**Writing convention:** All generated prose in KB files uses **one sentence per line** (semantic linebreaks).
This produces cleaner git diffs and makes review easier.

Example — do this:
```markdown
Sir Roderic is a paladin devoted to the Old Light.
He travels with a small band of adventurers through the Grimwild.
His faith wavers after the events at Ashenmoor.
```

Not this:
```markdown
Sir Roderic is a paladin devoted to the Old Light. He travels with a small band of adventurers through the Grimwild. His faith wavers after the events at Ashenmoor.
```

Bullet points, headings, and metadata lines are unaffected — only narrative prose gets one-sentence-per-line treatment.

---

## Workflow

Process one extracted session YAML through the following steps.

### Step 1 — Parse arguments & discover input

`$ARGUMENTS` format: `[yaml-file-path]`

- If a path is provided, use that file directly.
- If omitted, list files in `inbox/transcripts/extracted/` matching `session-*.yaml`.
  - Exclude `.gitkeep`.
  - If no extracted YAMLs exist, report that and stop.
  - If multiple extracted YAMLs exist, ask the user which one to process.

Session number, date, recap teaser, and all other data come from the YAML content — no additional arguments needed.

### Step 1b — Sync entity aliases

Run the alias sync script to ensure sub-entity names are in `entity-aliases.yaml`:

```bash
python3 scripts/sync_kb_aliases.py
```

This adds any missing sub-entity aliases (e.g., "The God of Ruin" → `old-gods` under `factions:`) so that entity resolution in later steps has the complete picture.

### Step 2 — Build KB index (context-efficient)

Minimize context usage by loading only what is needed:

| What to read | How |
|---|---|
| `config/entity-aliases.yaml` | Read in full (small config) |
| `config/speaker-map.yaml` | Read in full (small config) |
| `review/pending-changes.md` | Read in full (small file) |
| KB directories (`kb/pcs/`, `npcs/`, `locations/`, `items/`, `factions/`, `sessions/`, `story-arcs/group/`, `story-arcs/character/` (list subdirectories and their filenames), `world/`) | **List filenames only** (`ls`) — do NOT read contents |
| `gm-notes/` | **List filenames only** (`ls`) |
| Individual entity files | **Read on-demand** — only when you need to check or update a specific entity |
| Template files in `templates/` | **Read on-demand** — only when creating a new entity of that type |
| `kb/sessions/` | List arc subdirectories and their session files. Check for duplicate session number across ALL arc subfolders — if `session-{N}.md` exists anywhere, warn and stop |

This approach keeps context small and scales as the KB grows.

### Step 3 — Read & validate YAML

**3a** Read the extracted YAML file. Validate that required fields are present:
- `session_number`
- `date_played`
- `source_transcript`
- `summary`
- `major_events`

If any required field is missing, warn the user and stop.

**3b** Parse the YAML into working variables. The YAML is small (~1-2k tokens), so it fits entirely in context.

**3c** If `recap_teaser` is absent or empty, set it to `[TODO: Add recap-teaser]`.

### Step 4 — Map YAML fields to KB operations

Map each YAML field to the KB operations it drives:

| YAML Field | KB Operation |
|---|---|
| `summary`, `major_events` | Session file (Summary, Major Events) |
| `new_entities.npcs`, `new_entities.locations`, `new_entities.items`, `new_entities.factions` | Create entity files |
| `entity_updates` | Update existing entity files |
| `questions_raised` | Story hooks |
| `questions_resolved`, `arc_progress` | Story arc updates |
| `notable_quotes` | Session file (Notable Quotes) |
| `rules_clarifications` | PC files (Key Traits) if relevant; otherwise review in extracted YAML |
| `unresolved_references` | `review/pending-changes.md` |
| `gm_observations` | `gm-notes/` only (review in extracted YAML) |
| `filtered_sections` | Report only (not written to KB) |
| `recap_teaser` | Session file (Recap-Teaser) |

### Step 5 — Entity resolution (validation)

The extraction step pre-identified entities. This step validates them:

1. **Verify `entity_updates` targets exist** — For each entry in `entity_updates`, confirm the target entity has a file in the KB. If not, flag in `review/pending-changes.md`.
2. **Verify `new_entities` targets don't already exist** — For each entry in `new_entities`, confirm no existing KB file matches. If a match exists, convert to an `entity_updates` operation instead.
3. **Cross-check `unresolved_references`** — Check each entry against the full KB filename index. If you can now resolve one, move it to the appropriate category. If still ambiguous, keep it for `pending-changes.md`.
4. **Check `config/speaker-map.yaml`** to distinguish PCs from NPCs:
   - Any character listed under a player's `characters:` list is a **PC** → route to `kb/pcs/`.
   - All other characters are **NPCs** → route to `kb/npcs/`.

### Step 6 — Create session file

Read `templates/session.md`.
Fill in:

- **Number:** from `session_number`
- **Title:** synthesize a short, evocative title from `summary` and `major_events`
- **Date Played:** from `date_played`
- **Recap-Teaser:** from `recap_teaser`, or placeholder if absent
- **Summary:** from `summary`, reformatted with one sentence per line
- **Major Events:** from `major_events`, as a chronological bullet list
- **New Questions & Hooks:** from `questions_raised`
- **Questions Answered / Arcs Advanced:** from `questions_resolved` and `arc_progress`
- **Notable NPCs Introduced:** from `new_entities.npcs`, with `[[wiki-links]]` and brief descriptions
- **Notable Locations Visited:** from `new_entities.locations` plus locations mentioned in `major_events`, with `[[wiki-links]]`
- **Notable Quotes:** from `notable_quotes`, cleaned up with speaker attribution

**Determine the arc folder:**

Sessions live under arc subfolders — `kb/sessions/<arc-slug>/session-{N}.md`.

1. List subdirectories of `kb/sessions/` — each is an arc (e.g. `curse-of-ruin/`, `forgotten-and-forsaken/`).
2. Identify the **active arc** — the arc folder whose `index.md` has `**Status:** Active` or `**Status:** Beginning`, or (fallback) the arc containing the most recent session. If the newly resolved questions / arc_progress reference a different arc than the active one, ask the user which arc this session belongs to.
3. If no arc folder fits (e.g. a new arc is starting), ask the user for the arc name and slug, then create `kb/sessions/<arc-slug>/index.md` from a placeholder template before saving the session.

Save to `kb/sessions/<arc-slug>/session-{N}.md`.

**Quote rules:**

| Include | Exclude |
|---|---|
| Intentional, memorable in-character statements | Garbled STT fragments |
| Character personality moments | Generic "Yeah", "Okay" |
| Dramatic moments, humor | OOC rules discussion |

### Step 6b — Create new entity files

For each entry in `new_entities` (npcs, locations, items, factions):

1. Read the appropriate template from `templates/` (on-demand).
2. Fill in the template with information from the YAML entry.
3. Use the one-sentence-per-line convention for all prose sections.
4. Use `[[Entity Name]]` wiki-links for all cross-references.
5. Save to the correct KB directory with a slugified filename.
6. Set `**First Appeared:** [[Session N]]` where N is the current session number.

**Filename slugification rules:**
- Lowercase everything.
- Replace spaces with hyphens.
- Drop leading articles ("the", "a", "an").
- Remove all punctuation except hyphens.
- Examples: "Sir Roderic Lightbearer" → `sir-roderic-lightbearer.md`, "The Ashen Vale" → `ashen-vale.md`.

### Step 6c — Identify and create story hooks

A **hook** is a potential story arc that hasn't been activated in play yet — an open question, unresolved mystery, or thread that could become a full arc.

Hooks come from `questions_raised` in the YAML.

**Hooks vs Arc Open Questions:**

Before creating a hook, check if the question belongs to an **existing active arc**. If so, add it to that arc's "Open Questions" section instead of creating a separate hook.

- **Arc Open Questions:** Questions that will resolve as the current story progresses. "Can the spirit wall hold?" "Who was wearing Aldric's livery?" "Can the Seal reseal ruin?" — these are part of the Curse of Ruin arc.
- **Hooks:** Threads that could become their OWN story arc, independent of what's currently active. "What is the origin of the Greenholt Bloodline?" "What are the Witch Stones?" "Aldric's growing resentment of Garland" — these could develop into separate arcs.

**Test:** If the question would naturally resolve when the current arc concludes, it's an arc open question. If it could persist or develop regardless of how the current arc ends, it's a hook.

**What qualifies as a hook:**
- Unanswered questions about a character's past (unknown parentage, lost memories)
- Mysterious items or symbols with unexplained significance
- Unresolved mysteries (origin of a curse, purpose of an artifact)
- Goals a character wants to pursue (understand the Witch Stones, find a lost relative)
- Tensions or conflicts hinted at but not yet in play
- World events that could draw the party in

**What does NOT qualify as a hook:**
- Questions about how to resolve the current active arc
- Tactical questions ("Can we trust X?" "Will Y hold?")
- Questions that track progress within an active storyline
- Mysteries that are central to the current arc's plot

These belong in the relevant arc file's "Open Questions" section.

**Examples:**

✓ HOOK: "Aldric resents Garland's presence because it undermines his authority" → Could become a character arc about family legacy and succession
✓ HOOK: "The Greenholt Bloodline's mysterious origin" → Independent mystery that could develop into its own arc
✗ NOT A HOOK: "Can the Seal reseal ruin?" → Open question within the Curse of Ruin arc
✗ NOT A HOOK: "Is Marrow involved in releasing the ruin?" → Investigation thread within the current arc

**Classification:**
- **Group hooks** affect the whole party or world → `kb/story-arcs/group/hooks.md`
- **Character hooks** are tied to a specific PC → the `## Hooks` section of that PC's file in `kb/pcs/`

**Attribution rules — avoid duplicates and misclassification:**
- Attribute a hook to the character the hook is **about** (the subject), not every character who cares about it. If Character A has a personal goal related to Character B's mystery, that is part of Character A's motivation — not a separate hook. Do not create duplicate hooks covering the same underlying mystery from different character perspectives.
- A hook is only **group** if it affects the whole party or the world at large and is not primarily tied to 1–2 specific PCs' personal stories. If a hook involves specific PCs' backgrounds, bloodlines, or family history, it is a character hook for the most directly affected PC — even if multiple PCs share it.
- When a hook could reasonably belong to multiple PCs (e.g., a shared bloodline), place it under the PC with the strongest narrative connection (typically the one who is most likely to actively pursue it). Add a brief cross-reference in the other PC's hooks section rather than duplicating the full entry.

**Character hooks format** (in the PC's `## Hooks` section):

```markdown
### {Hook Name}
Brief description of what's unresolved and what could become a story arc.
One sentence per line.
```

**Group hooks format** (in `kb/story-arcs/group/hooks.md`):

```markdown
## {Hook Name}
**Source:** [[Session N]]
**Related:** [[Entity1]], [[Entity2]]

Brief description of what's unresolved and what could become a story arc.
One sentence per line.
```

Append new hooks if the section/file already exists. Do not duplicate hooks that are already listed.

**Hook → Arc lifecycle:**

When the YAML shows progress on an existing hook (via `arc_progress` or `questions_resolved`), consider promoting it to a full arc.
Remove the hook entry and create a dedicated arc file:
- Group: `kb/story-arcs/group/{arc-slug}.md`
- Character: `kb/story-arcs/character/{character-slug}/{arc-slug}.md`

The arc file uses `templates/story-arc.md`. Until activated, hooks remain in their current location.

**Relationship to pending-changes.md:**

Hooks capture things that *could* become story arcs. Do not flag clear hooks in `review/pending-changes.md` as "ambiguous content" — route them to the appropriate hooks location instead. Only flag in pending-changes if it's genuinely unclear whether something is a hook, or if you can't determine whether a hook is group vs. character.

### Step 7 — Propose entity aliases

For every new entity created, propose aliases in `config/entity-aliases.yaml`:

- Full canonical name (e.g., `"Sir Roderic Lightbearer": "sir-roderic-lightbearer"`)
- Short name (e.g., `"Roderic": "sir-roderic-lightbearer"`)
- Title variants (e.g., `"Sir Roderic": "sir-roderic-lightbearer"`)
- Do NOT propose generic descriptors (e.g., "the paladin", "the wizard", "the old man") as aliases.
  These are too ambiguous — multiple entities may share the same descriptor.
  If the GM wants a descriptor alias, they can add it manually after review.
- If the YAML `notable_quotes` or `entity_updates` suggest players consistently use a nickname, propose it as an alias (only if unambiguous — the nickname must clearly refer to a single entity).

Add aliases under the correct category section (`characters:`, `locations:`, `items:`, `factions:`).
Create a new category section if one doesn't exist yet.

All alias additions appear in the git diff for human review — never silently merge.

### Step 8 — Flag contradictions and ambiguous references

Add entries to `review/pending-changes.md` for:

- **Contradictions:** Information in the YAML that conflicts with existing KB content.
  ```markdown
  ## Contradictions
  - Session {N}: Says Castor is from the Northern Reaches, but pcs/castor.md says Southern Marches
  ```

- **Unresolved references:** From the YAML `unresolved_references` field — entity mentions that cannot be matched to existing entries or confidently identified as new.
  ```markdown
  ## Unresolved References
  - Session {N}: "the Shepherd's Teeth" — New location? Or alias for existing entity?
  ```

- **Ambiguous content:** Sections where it's unclear whether content is player-visible or GM-private.
  ```markdown
  ## Ambiguous Content
  - Session {N}: GM hints about a secret behind the ruins — player-visible mystery or GM-only info?
  ```

- **Missing context:** Information that seems incomplete or references unknown sessions/events.
  ```markdown
  ## Missing Context
  - Session {N}: References "the Pact of Thorns" but no details provided — placeholder entry created
  ```

### Step 9 — Update existing entity files

For each entry in `entity_updates`:

1. Read the existing entity file (on-demand).
2. **Incorporate new information** from `new_info` into the existing content — rewrite sections as needed so the file reads as a complete, up-to-date representation of the entity. Do not simply append to the end.
3. When new details expand on existing content, weave them into the relevant section to maintain a coherent narrative.
4. When new details supersede outdated information (e.g., a character's status changes), update the content in place.
5. If information genuinely conflicts and you cannot determine which is correct, keep the existing content and flag the contradiction in `review/pending-changes.md` (Step 8).
6. Maintain the one-sentence-per-line convention.
7. Preserve all existing `[[wiki-links]]` and add new ones as appropriate.
8. Update `## Session Appearances` on every PC and NPC that appears in the session.
9. Update `## Hooks` on PCs if the session introduces new hooks or resolves existing ones.

For `rules_clarifications` entries: extract relevant mechanical information to the appropriate PC file's Key Traits section.

**Avoid Notes sections:**
Do not add `## Notes` sections to entity files.
Information worth recording should go in the appropriate section:
- Tactical/behavioral info → Methods (NPCs)
- Physical details → Description
- Location features → Notable Features
- Session-specific events → Events Here / Key Events (with session link)

Transient session details (temporary barriers, items found during a scene) belong in the session file only — not duplicated to entity files.
Only update entity files with information that changes the permanent understanding of that entity.

### Step 10 — Split GM-private vs player-visible content

Route content based on sensitivity:

| Content | Destination |
|---|---|
| Published world facts, PC backstories, known NPC info | `kb/` (player-visible) |
| GM session prep, encounter plans, secret motivations | `gm-notes/` |
| Story arc — player-visible elements (open questions, known events) | `kb/story-arcs/` |
| Story arc — secret answers, future reveals, planned twists | `gm-notes/` (reference the arc file with a link) |
| Story hooks (open questions, mysteries the players know about) | `kb/story-arcs/` (player-visible) |
| GM answers to hooks, planned reveals for hooks | `gm-notes/` (reference the hooks file) |
| NPC secrets the players haven't learned | `gm-notes/` |
| `gm_observations` from YAML | Session file (Session Notes) for pacing/engagement observations; `gm-notes/` for plot-direction notes |

When content mixes both, split it: player-visible parts go to the KB, GM-private parts go to `gm-notes/`.
In the `gm-notes/` file, include a reference back to the related KB entry: `See also: [[Entity Name]]`.

If it's unclear whether content is player-visible or GM-private, flag it in `review/pending-changes.md` (Step 8) and default to placing it in `gm-notes/` (safer to keep private than to accidentally reveal).

**Note:** Most session content is inherently player-visible since players were present.
GM-private content from sessions is rare — mainly meta-observations about plot direction, pacing notes, or things the GM noticed that players didn't.

### Step 11 — Move processed files

**Pre-move checklist** — verify all of the following before moving:

- [ ] All YAML fields have been processed (nothing skipped).
- [ ] Session file has been created with all template sections filled.
- [ ] New entity files have been created for all entries in `new_entities`.
- [ ] Existing entity files have been updated for all entries in `entity_updates`.
- [ ] Alias proposals have been added to `entity-aliases.yaml`.
- [ ] Contradictions and unresolved references have been flagged in `pending-changes.md`.
- [ ] GM-private content has been routed to `gm-notes/`.
- [ ] Story hooks have been identified and added to the appropriate location (PC files for character hooks, hooks.md for group hooks).
- [ ] All generated prose uses one-sentence-per-line.
- [ ] All entity references use `[[wiki-link]]` syntax.

Once verified, move the YAML file:

```
inbox/transcripts/extracted/session-{N}.yaml → inbox/transcripts/processed/session-{N}.yaml
```

The prepared transcript stays in `inbox/transcripts/prepared/` — it serves as an archival source for potential re-extraction. The `source_transcript` field in the YAML references its path.

### Step 12 — Report summary

After processing, report:

```
## Processed: {yaml filename}

**Session:** {number} — {title}
**Date Played:** {date}
**Source YAML:** {yaml path} ({token estimate})
**Source Transcript:** {source_transcript from YAML}
**Filtered sections:** {count from filtered_sections} ({total lines} lines skipped during extraction)

**Files created:**
- kb/sessions/{arc-slug}/session-{N}.md
- ...

**Files updated:**
- ...

**Aliases proposed:**
- ...

**Items flagged for review:**
- ...

**Story hooks identified / activated:**
- ...

**Notable quotes extracted:** {count}

**GM-private content:**
- ...
```

---

## Edge Cases

**Rules discussions as PC data:**
When `rules_clarifications` entries describe abilities, class features, or mechanical details that should be recorded permanently, extract the relevant information to PC files (Key Traits section).
Most rules clarifications are GM rulings to verify later — these stay in the extracted YAML for review and are not written to KB files.

**Ambiguous entity type:**
If it's unclear whether a named entity is a person, location, faction, etc., flag it in `pending-changes.md` and make your best guess for initial placement.
The human reviewer can move it.

**PC vs NPC detection:**
Always check `config/speaker-map.yaml` first.
Any character listed under a player entry is a PC.
If a character is not in the speaker map and the YAML doesn't clarify, default to NPC and flag for review.

**Story arcs with secrets:**
Split the arc into two parts:
- Player-visible arc file in `kb/story-arcs/` with known facts and open questions.
- GM-private file in `gm-notes/` with answers, planned reveals, and secret motivations.
The GM-private file should reference the arc: `See also: [[Arc Name]]`.

**Session with no major events:**
Provide an honest summary even if little happened.
It is fine for the Major Events section to have fewer items.

**Recap-teaser not provided:**
Use the placeholder `[TODO: Add recap-teaser]` in the session file.
Do not fabricate a teaser.

**Entity mentioned but not introduced:**
If an entity appears in `unresolved_references` and only shows up as a passing mention, do not create a full entity file.
Only create files for entities in `new_entities`.

**Duplicate session number:**
If `session-{N}.md` already exists in ANY arc subfolder under `kb/sessions/`, warn the user and stop.
Do not overwrite existing session files.

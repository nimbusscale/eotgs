# Skill: Incorporate Notes

**Purpose:** Process markdown notes from `inbox/notes/` into the Grimwild campaign knowledge base, one file at a time.

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

Process each note file individually through the following steps.

### Step 1 — Discover notes

List files in `inbox/notes/`.
Exclude the `processed/` subdirectory and `.gitkeep`.
If no unprocessed notes exist, report that and stop.
Process notes **one at a time** in alphabetical order.

### Step 2 — Build KB index (context-efficient)

Minimize context usage by loading only what is needed:

| What to read | How |
|---|---|
| `config/entity-aliases.yaml` | Read in full (small config) |
| `config/speaker-map.yaml` | Read in full (small config) |
| `review/pending-changes.md` | Read in full (small file) |
| KB directories (`grimwild-kb/pcs/`, `npcs/`, `locations/`, `items/`, `factions/`, `sessions/`, `story-arcs/group/`, `story-arcs/character/`, `world/`) | **List filenames only** (`ls`) — do NOT read contents |
| `gm-notes/` | **List filenames only** (`ls`) |
| Individual entity files | **Read on-demand** — only when the note references that entity and you need to check or update it |
| Template files in `templates/` | **Read on-demand** — only when creating a new entity of that type |

This approach keeps context small and scales as the KB grows.

### Step 3 — Analyze the note

Read the note file and classify its content.
A single note may contain multiple content types.
Break the note into logical sections and classify each:

| Content type | Primary destination | Template |
|---|---|---|
| Session prep / GM plans | `gm-notes/` | — (freeform) |
| World-building (geography, history, gods, cultures) | `grimwild-kb/world/` | `templates/world-entry.md` |
| New PC info | `grimwild-kb/pcs/` | `templates/pc.md` |
| New NPC info | `grimwild-kb/npcs/` | `templates/npc.md` |
| Updates to existing characters | Existing file in `pcs/` or `npcs/` | — (append to existing) |
| New location | `grimwild-kb/locations/` | `templates/location.md` |
| New item | `grimwild-kb/items/` | `templates/item.md` |
| New faction | `grimwild-kb/factions/` | `templates/faction.md` |
| Story arc (player-visible) | `grimwild-kb/story-arcs/group/` or `story-arcs/character/` | `templates/story-arc.md` |
| Story arc (GM secrets) | `gm-notes/` | — (freeform, reference the arc) |
| Session recap or summary | `grimwild-kb/sessions/` | `templates/session.md` |

### Step 4 — Resolve entity references

For every entity name mentioned in the note:

1. Check `config/entity-aliases.yaml` for a canonical match.
2. Check KB directory filenames for a slug match (e.g., "Edric Bloom" → `edric-bloom.md` in `pcs/`).
3. Check `config/speaker-map.yaml` to distinguish PCs from NPCs:
   - Any character listed under a player's `characters:` list is a **PC** → route to `grimwild-kb/pcs/`.
   - All other characters are **NPCs** → route to `grimwild-kb/npcs/`.
4. If no match is found, flag the reference as unresolved (see Step 7).

### Step 5 — Create new entity files

When the note introduces an entity that does not yet exist in the KB:

1. Read the appropriate template from `templates/` (on-demand).
2. Fill in the template with information from the note.
3. Use the one-sentence-per-line convention for all prose sections.
4. Use `[[Entity Name]]` wiki-links for all cross-references.
5. Save to the correct KB directory with a slugified filename.

**Filename slugification rules:**
- Lowercase everything.
- Replace spaces with hyphens.
- Drop leading articles ("the", "a", "an").
- Remove all punctuation except hyphens.
- Examples: "Sir Roderic Lightbearer" → `sir-roderic-lightbearer.md`, "The Ashen Vale" → `ashen-vale.md`.

### Step 6 — Propose entity aliases

For every new entity created, propose aliases in `config/entity-aliases.yaml`:

- Full canonical name (e.g., `"Sir Roderic Lightbearer": "sir-roderic-lightbearer"`)
- Short name (e.g., `"Roderic": "sir-roderic-lightbearer"`)
- Title variants (e.g., `"Sir Roderic": "sir-roderic-lightbearer"`)
- Do NOT propose generic descriptors (e.g., "the paladin", "the wizard", "the old man") as aliases.
  These are too ambiguous — multiple entities may share the same descriptor.
  If the GM wants a descriptor alias, they can add it manually after review.

Add aliases under the correct category section (`characters:`, `locations:`, `items:`, `factions:`).
Create a new category section if one doesn't exist yet.

All alias additions appear in the git diff for human review — never silently merge.

### Step 7 — Flag contradictions and ambiguous references

Add entries to `review/pending-changes.md` for:

- **Contradictions:** Information in the note that conflicts with existing KB content.
  ```markdown
  ## Contradictions
  - inbox/notes/session-zero-prep.md: Says Castor is from the Northern Reaches, but pcs/castor.md says Southern Marches
  ```

- **Unresolved references:** Entity names that cannot be matched to existing entries or confidently identified as new.
  ```markdown
  ## Unresolved References
  - inbox/notes/session-zero-prep.md: "the Shepherd's Teeth" — New location? Or alias for existing entity?
  ```

- **Ambiguous content:** Sections where it's unclear whether content is player-visible or GM-private.
  ```markdown
  ## Ambiguous Content
  - inbox/notes/session-zero-prep.md: Story arc "The Missing Caravan" includes plot twists — split into player-visible arc + GM secret, or keep entirely in gm-notes/?
  ```

- **Missing context:** Information that seems incomplete or references unknown sessions/events.
  ```markdown
  ## Missing Context
  - inbox/notes/world-ideas.md: References "the Pact of Thorns" but no details provided — placeholder entry created
  ```

### Step 8 — Update existing entity files

When the note contains information about an entity that already exists in the KB:

1. Read the existing entity file (on-demand).
2. **Incorporate new information** into the existing content — rewrite sections as needed so the file reads as a complete, up-to-date representation of the entity. Do not simply append to the end.
3. When new details expand on existing content, weave them into the relevant section to maintain a coherent narrative.
4. When new details supersede outdated information (e.g., a character's status changes), update the content in place.
5. If information genuinely conflicts and you cannot determine which is correct, keep the existing content and flag the contradiction in `review/pending-changes.md` (Step 7).
6. Maintain the one-sentence-per-line convention.
7. Preserve all existing `[[wiki-links]]` and add new ones as appropriate.

### Step 9 — Split GM-private vs player-visible content

Route content based on sensitivity:

| Content | Destination |
|---|---|
| Published world facts, PC backstories, known NPC info | `grimwild-kb/` (player-visible) |
| GM session prep, encounter plans, secret motivations | `gm-notes/` |
| Story arc — player-visible elements (open questions, known events) | `grimwild-kb/story-arcs/` |
| Story arc — secret answers, future reveals, planned twists | `gm-notes/` (reference the arc file with a link) |
| NPC secrets the players haven't learned | `gm-notes/` |

When a note mixes both, split it: player-visible parts go to the KB, GM-private parts go to `gm-notes/`.
In the `gm-notes/` file, include a reference back to the related KB entry: `See also: [[Entity Name]]`.

If it's unclear whether content is player-visible or GM-private, flag it in `review/pending-changes.md` (Step 7) and default to placing it in `gm-notes/` (safer to keep private than to accidentally reveal).

### Step 10 — Move processed note

**Pre-move checklist** — verify all of the following before moving:

- [ ] All sections of the note have been processed (nothing skipped).
- [ ] New entity files have been created for all new entities found.
- [ ] Existing entity files have been updated where applicable.
- [ ] Alias proposals have been added to `entity-aliases.yaml`.
- [ ] Contradictions and ambiguous references have been flagged in `pending-changes.md`.
- [ ] GM-private content has been routed to `gm-notes/`.
- [ ] All generated prose uses one-sentence-per-line.
- [ ] All entity references use `[[wiki-link]]` syntax.

Once verified, move the note:

```
inbox/notes/{filename} → inbox/notes/processed/{YYYY-MM-DD}/{filename}
```

Create the date subdirectory if it doesn't exist.
Use today's date (the date of processing, not the date the note was written).

### Step 11 — Report summary

After processing each note, report:

```
## Processed: {filename}

**Files created:**
- grimwild-kb/pcs/edric-bloom.md
- grimwild-kb/locations/ashen-vale.md

**Files updated:**
- grimwild-kb/pcs/castor.md (added backstory details)

**Aliases proposed:**
- "Edric" → edric-bloom (characters)
- "Ashen Vale" → ashen-vale (locations)

**Items flagged for review:**
- Contradiction: Castor's homeland (see review/pending-changes.md)
- Unresolved reference: "the Shepherd's Teeth"

**GM-private content:**
- gm-notes/session-zero-prep.md (encounter plans)
```

---

## Edge Cases

**Ambiguous entity type:**
If it's unclear whether a named entity is a person, location, faction, etc., flag it in `pending-changes.md` and make your best guess for initial placement.
The human reviewer can move it.

**PC vs NPC detection:**
Always check `config/speaker-map.yaml` first.
Any character listed under a player entry is a PC.
If a character is not in the speaker map and the note doesn't clarify, default to NPC and flag for review.

**Story arcs with secrets:**
Split the arc into two parts:
- Player-visible arc file in `grimwild-kb/story-arcs/` with known facts and open questions.
- GM-private file in `gm-notes/` with answers, planned reveals, and secret motivations.
The GM-private file should reference the arc: `See also: [[Arc Name]]`.

**Missing session context:**
Notes may reference sessions that don't have session files yet.
Create `[[Session X]]` links anyway — they serve as forward references.
Do not create empty session files just to resolve links.

**Multiple content types in one note:**
A single note often contains several types of content (e.g., PC backstories + world-building + session prep).
Process each section independently and route to the correct destination.

**Empty or trivial notes:**
If a note contains only a title or a few words with no actionable content, move it to `processed/` and report "No actionable content found."

**Duplicate information:**
If the note repeats information already in the KB, skip the duplicate content silently.
Only flag if the repeated information is slightly different (potential contradiction).

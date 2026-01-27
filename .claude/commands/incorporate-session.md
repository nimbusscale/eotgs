# Skill: Incorporate Session

**Purpose:** Process a filtered session transcript from `inbox/transcripts/filtered/` into the Grimwild campaign knowledge base — creating a session file, updating entities, tracking story arcs, and extracting hooks.

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

Process one filtered transcript through the following steps.

### Step 1 — Parse arguments & discover transcript

`$ARGUMENTS` format: `<session-number> [recap-teaser text...]`

- Example: `1 The dust settles over what was once Ashbrook...`
- If session number is missing, prompt the user and stop.
- Recap-teaser is everything after the number; if absent, leave a placeholder `[TODO: Add recap-teaser]` in the session file.

List files in `inbox/transcripts/filtered/`.
Exclude `.gitkeep`.
If no filtered transcripts exist, report that and stop.
If multiple filtered transcripts exist, ask the user which one to process.

Extract the session date from the first timestamped line in the transcript.
Expected format: `[M/DD/YYYY H:MM AM/PM]`.

### Step 2 — Build KB index (context-efficient)

Minimize context usage by loading only what is needed:

| What to read | How |
|---|---|
| `config/entity-aliases.yaml` | Read in full (small config) |
| `config/speaker-map.yaml` | Read in full (small config) |
| `review/pending-changes.md` | Read in full (small file) |
| KB directories (`grimwild-kb/pcs/`, `npcs/`, `locations/`, `items/`, `factions/`, `sessions/`, `story-arcs/group/`, `story-arcs/character/` (list subdirectories and their filenames), `world/`) | **List filenames only** (`ls`) — do NOT read contents |
| `gm-notes/` | **List filenames only** (`ls`) |
| Individual entity files | **Read on-demand** — only when the transcript references that entity and you need to check or update it |
| Template files in `templates/` | **Read on-demand** — only when creating a new entity of that type |
| `grimwild-kb/sessions/` | Check for duplicate session number collision — if `session-{N}.md` already exists, warn and stop |

This approach keeps context small and scales as the KB grows.

### Step 3 — Read & pre-process transcript

**3a** Read the full transcript. Note the total line count.

**3b** Strip NON-GAME sections (between `<!-- NON-GAME SECTION -->` / `<!-- END NON-GAME SECTION -->` markers).
Skip these during analysis.
Count the stripped lines for the final report.

**3c** Build speaker-to-entity map from `config/speaker-map.yaml`:

| Transcript Speaker | Entity | Type |
|---|---|---|
| GM | (narrator) | GM |
| Garland | Garland yn Greenholt | PC |
| Edric | Edric Bloom | PC |
| Roderic | Sir Roderic Lightbearer | PC |
| Castor | Castor | PC |

**3d** Speech-to-text handling: interpret meaning behind fragmented speech.
Do not treat garbled output as literal text.
Synthesize across multiple fragmented lines to extract intended meaning.

### Step 4 — Analyze transcript content

Read through the game-relevant portions and classify content:

| Content type | How to identify | Destination |
|---|---|---|
| GM narration / events | GM describes scenes, actions | Session file (Summary, Major Events) |
| World-building discussion | Geography, history, culture | `grimwild-kb/world/` or entity files |
| New NPC introduction | GM introduces named character | `grimwild-kb/npcs/` |
| New location | New place visited/described | `grimwild-kb/locations/` |
| New item | Named item appears | `grimwild-kb/items/` |
| New faction | Named group appears | `grimwild-kb/factions/` |
| PC development | Players reveal character details | Update `grimwild-kb/pcs/` |
| Story arc progress | Events advance/complicate arcs | Update `grimwild-kb/story-arcs/` |
| New story hooks | Unanswered questions, mysteries | `story-arcs/group/hooks.md` or `character/*/hooks.md` |
| Rules/mechanical details | Ability usage, class features | Update PC file (Key Traits) |
| Notable quotes | Memorable in-character lines | Session file (Notable Quotes) |

Track scene transitions for chronological summary organization.

### Step 5 — Resolve entity references

For every entity name mentioned in the transcript:

1. Check `config/entity-aliases.yaml` for a canonical match.
2. Check KB directory filenames for a slug match (e.g., "Edric Bloom" → `edric-bloom.md` in `pcs/`).
3. Check `config/speaker-map.yaml` to distinguish PCs from NPCs:
   - Any character listed under a player's `characters:` list is a **PC** → route to `grimwild-kb/pcs/`.
   - All other characters are **NPCs** → route to `grimwild-kb/npcs/`.
4. If no match is found, flag the reference as unresolved (see Step 8).

Add: fuzzy matching for speech-to-text misspellings (e.g., "Ashton Vale" → "Ashen Vale").
Check `config/speaker-map.yaml` `transcription_corrections` for known STT errors.

### Step 6 — Create session file

Read `templates/session.md`.
Fill in:

- **Number:** from `$ARGUMENTS`
- **Title:** synthesize a short, evocative title from the session's major events
- **Date Played:** extracted from transcript timestamps (Step 1)
- **Recap-Teaser:** from `$ARGUMENTS`, or placeholder if absent
- **Summary:** 2-3 paragraph narrative of the session, one sentence per line
- **Major Events:** chronological bullet list of key events
- **New Questions & Hooks:** open threads introduced this session
- **Questions Answered / Arcs Advanced:** resolved or progressed threads
- **NPCs Introduced:** with `[[wiki-links]]` and brief descriptions
- **Locations Visited:** with `[[wiki-links]]`
- **Notable Quotes:** cleaned-up memorable lines with speaker attribution
- **Session Notes:** GM observations about pacing, player engagement, things to revisit

Save to `grimwild-kb/sessions/session-{N}.md`.

**Quote extraction rules:**

| Include | Exclude |
|---|---|
| Intentional, memorable in-character statements | Garbled STT fragments |
| Character personality moments | Generic "Yeah", "Okay" |
| Dramatic moments, humor | OOC rules discussion |

### Step 6b — Create new entity files

When the transcript introduces an entity that does not yet exist in the KB:

1. Read the appropriate template from `templates/` (on-demand).
2. Fill in the template with information from the transcript.
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

**What qualifies as a hook:**
- Unanswered questions about a character's past (unknown parentage, lost memories)
- Mysterious items or symbols with unexplained significance
- Unresolved mysteries (origin of a curse, purpose of an artifact)
- Goals a character wants to pursue (understand the Witch Stones, find a lost relative)
- Tensions or conflicts hinted at but not yet in play
- World events that could draw the party in

**Classification:**
- **Group hooks** affect the whole party or world → `grimwild-kb/story-arcs/group/hooks.md`
- **Character hooks** are tied to a specific PC → `grimwild-kb/story-arcs/character/{character-slug}/hooks.md`

**Attribution rules — avoid duplicates and misclassification:**
- Attribute a hook to the character the hook is **about** (the subject), not every character who cares about it. If Character A has a personal goal related to Character B's mystery, that is part of Character A's motivation — not a separate hook. Do not create duplicate hooks covering the same underlying mystery from different character perspectives.
- A hook is only **group** if it affects the whole party or the world at large and is not primarily tied to 1–2 specific PCs' personal stories. If a hook involves specific PCs' backgrounds, bloodlines, or family history, it is a character hook for the most directly affected PC — even if multiple PCs share it.
- When a hook could reasonably belong to multiple PCs (e.g., a shared bloodline), place it under the PC with the strongest narrative connection (typically the one who is most likely to actively pursue it). Add a brief cross-reference in the other PC's hooks file rather than duplicating the full entry.

**Directory structure:**
- Always create a subdirectory for every PC listed in `speaker-map.yaml` under `story-arcs/character/` (using the character's filename slug)
- `grimwild-kb/story-arcs/group/hooks.md`
- `grimwild-kb/story-arcs/character/castor/hooks.md`
- `grimwild-kb/story-arcs/character/edric-bloom/hooks.md`
- etc.

**Hooks file format:**

```markdown
# Hooks

## {Hook Name}
**Source:** [[Session N]]
**Related:** [[Entity1]], [[Entity2]]

Brief description of what's unresolved and what could become a story arc.
One sentence per line.
```

Append new hooks to an existing `hooks.md` if one already exists. Do not duplicate hooks that are already listed.

**Hook → Arc lifecycle:**

When the transcript shows the party engaging with an existing hook, consider promoting it to a full arc.
Remove the hook entry from `hooks.md` and create a dedicated arc file:
- Group: `grimwild-kb/story-arcs/group/{arc-slug}.md`
- Character: `grimwild-kb/story-arcs/character/{character-slug}/{arc-slug}.md`

The arc file uses `templates/story-arc.md`. Until activated, hooks remain as entries in `hooks.md`.

**Relationship to pending-changes.md:**

Hooks capture things that *could* become story arcs. Do not flag clear hooks in `review/pending-changes.md` as "ambiguous content" — route them to hooks.md instead. Only flag in pending-changes if it's genuinely unclear whether something is a hook, or if you can't determine whether a hook is group vs. character.

### Step 7 — Propose entity aliases

For every new entity created, propose aliases in `config/entity-aliases.yaml`:

- Full canonical name (e.g., `"Sir Roderic Lightbearer": "sir-roderic-lightbearer"`)
- Short name (e.g., `"Roderic": "sir-roderic-lightbearer"`)
- Title variants (e.g., `"Sir Roderic": "sir-roderic-lightbearer"`)
- Do NOT propose generic descriptors (e.g., "the paladin", "the wizard", "the old man") as aliases.
  These are too ambiguous — multiple entities may share the same descriptor.
  If the GM wants a descriptor alias, they can add it manually after review.
- If players consistently use a nickname during the session, propose it as an alias (only if unambiguous — the nickname must clearly refer to a single entity).

Add aliases under the correct category section (`characters:`, `locations:`, `items:`, `factions:`).
Create a new category section if one doesn't exist yet.

All alias additions appear in the git diff for human review — never silently merge.

### Step 8 — Flag contradictions and ambiguous references

Add entries to `review/pending-changes.md` for:

- **Contradictions:** Information in the transcript that conflicts with existing KB content.
  ```markdown
  ## Contradictions
  - Session {N} transcript: Says Castor is from the Northern Reaches, but pcs/castor.md says Southern Marches
  ```

- **Unresolved references:** Entity names that cannot be matched to existing entries or confidently identified as new.
  ```markdown
  ## Unresolved References
  - Session {N} transcript: "the Shepherd's Teeth" — New location? Or alias for existing entity?
  ```

- **Ambiguous content:** Sections where it's unclear whether content is player-visible or GM-private.
  ```markdown
  ## Ambiguous Content
  - Session {N} transcript: GM hints about a secret behind the ruins — player-visible mystery or GM-only info?
  ```

- **Missing context:** Information that seems incomplete or references unknown sessions/events.
  ```markdown
  ## Missing Context
  - Session {N} transcript: References "the Pact of Thorns" but no details provided — placeholder entry created
  ```

### Step 9 — Update existing entity files

When the transcript contains information about an entity that already exists in the KB:

1. Read the existing entity file (on-demand).
2. **Incorporate new information** into the existing content — rewrite sections as needed so the file reads as a complete, up-to-date representation of the entity. Do not simply append to the end.
3. When new details expand on existing content, weave them into the relevant section to maintain a coherent narrative.
4. When new details supersede outdated information (e.g., a character's status changes), update the content in place.
5. If information genuinely conflicts and you cannot determine which is correct, keep the existing content and flag the contradiction in `review/pending-changes.md` (Step 8).
6. Maintain the one-sentence-per-line convention.
7. Preserve all existing `[[wiki-links]]` and add new ones as appropriate.
8. Update `## Session Appearances` on every PC and NPC that appears in the session.
9. Update `## Current Threads` on PCs if the session changes their active storylines.

### Step 10 — Split GM-private vs player-visible content

Route content based on sensitivity:

| Content | Destination |
|---|---|
| Published world facts, PC backstories, known NPC info | `grimwild-kb/` (player-visible) |
| GM session prep, encounter plans, secret motivations | `gm-notes/` |
| Story arc — player-visible elements (open questions, known events) | `grimwild-kb/story-arcs/` |
| Story arc — secret answers, future reveals, planned twists | `gm-notes/` (reference the arc file with a link) |
| Story hooks (open questions, mysteries the players know about) | `grimwild-kb/story-arcs/` (player-visible) |
| GM answers to hooks, planned reveals for hooks | `gm-notes/` (reference the hooks file) |
| NPC secrets the players haven't learned | `gm-notes/` |

When transcript content mixes both, split it: player-visible parts go to the KB, GM-private parts go to `gm-notes/`.
In the `gm-notes/` file, include a reference back to the related KB entry: `See also: [[Entity Name]]`.

If it's unclear whether content is player-visible or GM-private, flag it in `review/pending-changes.md` (Step 8) and default to placing it in `gm-notes/` (safer to keep private than to accidentally reveal).

**Note:** Most transcript content is inherently player-visible since players were present for the session.
GM-private content from transcripts is rare — mainly meta-observations about plot direction, pacing notes, or things the GM noticed that players didn't.

### Step 11 — Move processed transcript

**Pre-move checklist** — verify all of the following before moving:

- [ ] All game-relevant sections of the transcript have been processed (nothing skipped).
- [ ] Session file has been created with all template sections filled.
- [ ] New entity files have been created for all new entities found.
- [ ] Existing entity files have been updated where applicable.
- [ ] Alias proposals have been added to `entity-aliases.yaml`.
- [ ] Contradictions and ambiguous references have been flagged in `pending-changes.md`.
- [ ] GM-private content has been routed to `gm-notes/`.
- [ ] Story hooks have been identified and added to the appropriate hooks.md files.
- [ ] All generated prose uses one-sentence-per-line.
- [ ] All entity references use `[[wiki-link]]` syntax.

Once verified, move the transcript:

```
inbox/transcripts/filtered/{filename} → inbox/transcripts/processed/{YYYY-MM-DD}/{filename}
```

Create the date subdirectory if it doesn't exist.
Use today's date (the date of processing, not the date the session was played).

### Step 12 — Report summary

After processing, report:

```
## Processed: {filename}

**Session:** {number} — {title}
**Date Played:** {date}
**Transcript lines:** {total} ({game} game, {non-game} non-game skipped)

**Files created:**
- grimwild-kb/sessions/session-{N}.md
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

**Speech-to-text quality:**
Interpret intent, not literal garbled text.
Use surrounding context to reconstruct meaning from fragmented STT output.
Check `config/speaker-map.yaml` `transcription_corrections` for known errors.

**Player OOC vs in-character:**
Use context to distinguish out-of-character discussion from in-character speech.
Do not extract OOC banter as notable quotes.
Rules discussions are OOC but may contain useful mechanical data for PC files.

**Rules discussions as PC data:**
When players discuss abilities, class features, or mechanical details, extract the relevant information for PC files (Key Traits section).
Do not include the rules discussion itself in the session summary.

**Ambiguous entity type:**
If it's unclear whether a named entity is a person, location, faction, etc., flag it in `pending-changes.md` and make your best guess for initial placement.
The human reviewer can move it.

**PC vs NPC detection:**
Always check `config/speaker-map.yaml` first.
Any character listed under a player entry is a PC.
If a character is not in the speaker map and the transcript doesn't clarify, default to NPC and flag for review.

**Story arcs with secrets:**
Split the arc into two parts:
- Player-visible arc file in `grimwild-kb/story-arcs/` with known facts and open questions.
- GM-private file in `gm-notes/` with answers, planned reveals, and secret motivations.
The GM-private file should reference the arc: `See also: [[Arc Name]]`.

**Overlapping speakers / crosstalk:**
When multiple speakers talk rapidly over each other, synthesize the meaningful content across the rapid-fire lines.
Do not try to preserve exact turn-by-turn ordering when it's garbled.

**Long transcripts:**
Process in chronological chunks, maintaining a running entity/event list across chunks.
Do not lose track of entities mentioned earlier in the transcript.

**Session with no major events:**
Provide an honest summary even if little happened.
It is fine for the Major Events section to have fewer items.

**Recap-teaser not provided:**
Use the placeholder `[TODO: Add recap-teaser]` in the session file.
Do not fabricate a teaser.

**Entity mentioned but not introduced:**
If an entity is only mentioned in passing (e.g., "I heard about the Black Tower once"), do not create a full entity file.
Only create files for entities that are meaningfully introduced — described, interacted with, or plot-relevant.

**Duplicate session number:**
If `grimwild-kb/sessions/session-{N}.md` already exists, warn the user and stop.
Do not overwrite existing session files.

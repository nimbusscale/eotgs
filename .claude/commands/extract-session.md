# Skill: Extract Session

**Purpose:** Filter non-game content and extract structured session data from a prepared transcript, producing a small YAML file that the `incorporate-session` skill can efficiently process.

**Input:** A prepared transcript from `inbox/transcripts/prepared/`

**Output:** A structured YAML file in `inbox/transcripts/extracted/`

**Architecture:** Orchestrator pattern — the main agent never reads raw transcript text. A Python chunker splits the transcript into ~800-line chunks. Subagents (Task tool) each process one chunk in isolated context and write small per-chunk YAML results. The main agent reads only the small results and consolidates them.

---

## Workflow

### Step 1 — Parse arguments & discover transcript

`$ARGUMENTS` format:
```
<session-number> [YYYY-MM-DD]
[optional recap/teaser text on subsequent lines]
```

- **First line:** session number (required) and optional date — sets `session_number` and `date_played` in the YAML output.
- **Subsequent lines (if any):** treated as a **provided recap/teaser**. This is GM-written prose that will be used as the `recap_teaser` value and as an authoritative reference for entity spelling during extraction.
- Date is optional — if omitted, it will be extracted from the transcript by a subagent.
- If session number is missing, prompt the user and stop.

List files in `inbox/transcripts/prepared/`.
Exclude `.gitkeep`.
If no prepared transcripts exist, report that and stop.
If multiple prepared transcripts exist, ask the user which one to process.

### Step 2 — Load chunks

Check if `inbox/transcripts/chunks/session-{N}-manifest.json` already exists (created by `ingest_transcript.py`).

If not, run the chunker as fallback:
```bash
python3 scripts/chunk_transcript.py --session N --input <prepared-transcript-path>
```

Read the manifest JSON. It contains:
- `session` — session number
- `source_transcript` — path to the prepared transcript
- `total_lines` — total line count
- `chunk_count` — number of chunks
- `known_entities` — dict of entity names by category (pcs, npcs_and_others, locations, items, factions, world)
- `kb_filenames` — dict of KB filenames by subdirectory
- `sub_entity_map` — dict mapping sub-entity header names to `{"parent_file", "parent_name", "category"}` (e.g., `"The God of Ruin" → {"parent_file": "factions/old-gods.md", "parent_name": "Old Gods", "category": "factions"}`)
- `kb_content_hints` — dict mapping KB file paths to lists of sub-entity section names (e.g., `"factions/old-gods.md" → ["The God of Ruin", "The Harlequins", ...]`)
- `campaign_context` — contents of `exports/campaign-index.md` (empty string if file doesn't exist)
- `chunks` — list of per-chunk info: `chunk_index`, `file`, `line_start`, `line_end`, `line_count`, `entities_mentioned`

Also read `config/speaker-map.yaml` for the PC list and transcription corrections (needed for subagent prompts).

### Step 3 — Spawn subagents (one per chunk)

Launch one Task subagent per chunk using `subagent_type: "general-purpose"`. Launch as many in parallel as possible (the Task tool supports multiple parallel calls in a single message).

Each subagent's prompt must include everything it needs to process its chunk independently. Build each prompt from the template below, substituting values from the manifest and config.

**IMPORTANT:** Each subagent writes its result to a YAML file at `inbox/transcripts/chunks/session-{N}-result-{chunk_index}.yaml`. The main agent reads these files after all subagents complete — it does NOT rely on the subagent's return text for the structured data.

#### Subagent Prompt Template

Build the prompt for each subagent by assembling these sections. Replace `{...}` placeholders with actual values.

````
You are extracting structured data from one chunk of a TTRPG session transcript. Read the chunk, filter non-game content, and write a structured YAML result file.

## Your chunk

Read the file: `{chunk_file_path}`
This is chunk {chunk_index} of {chunk_count} (lines {line_start}-{line_end} of {total_lines} total).
Write your result to: `inbox/transcripts/chunks/session-{session_number}-result-{chunk_index}.yaml`

## Player characters

{For each player in speaker-map.yaml, list: display name, full character name, player name}

## Transcription corrections

These are known speech-to-text errors. When you see the "match" text, the correct word is the "replace" text:
{List each correction from speaker-map.yaml transcription_corrections}

## Known entities

These entities already exist in the knowledge base. If you see them mentioned, record updates under `entity_updates`, NOT under `new_entities`.

**PCs:** {comma-separated list from manifest known_entities.pcs}
**NPCs/Characters:** {comma-separated list from manifest known_entities.npcs_and_others}
**Locations:** {comma-separated list from manifest known_entities.locations}
**Items:** {comma-separated list from manifest known_entities.items}
**Factions:** {comma-separated list from manifest known_entities.factions}
**World:** {comma-separated list from manifest known_entities.world}

**KB files:** {For each KB subdirectory with files, list: "subdir/: file1.md, file2.md, ..."}

## KB file contents (sub-entities)

These section headers exist inside KB files. They represent sub-entries within larger entries.
If you encounter these names OR closely related names in the transcript, record them as
`entity_updates` for the parent entity — NOT as `new_entities`.

{For each entry in sub_entity_map:}
- **{name}** → part of {parent_name} (`{parent_file}`)

**Key files and their sections:**
{For each file in kb_content_hints with entries:}
`{file_path}`: {comma-separated section names}

## Campaign context

{Insert campaign_context from manifest verbatim. If empty, write: "This is a new campaign — no prior context available."}

{If recap/teaser was provided by user, add:}
## Provided recap/teaser (authoritative spelling reference)

The GM provided this recap/teaser text. Treat entity spellings in this text as authoritative — they override STT spellings from the transcript when there's a conflict.

```
{recap/teaser text}
```

## Extraction rules

### What to filter out (log to `filtered_sections`)

- Real-world chit-chat unrelated to the game
- AFK breaks ("getting water", "bathroom break")
- Technical issues ("can you hear me?", "Discord is lagging")
- Scheduling talk ("same time next week?")
- Extended off-topic tangents (TV shows, news, personal stories)

### What to keep (game-related)

- In-character dialogue and narration
- Rules discussions and clarifications
- Character ability discussions
- World-building discussion
- Dice roll announcements and results
- Session planning within the game context
- Jokes/banter that reference game content

**When uncertain, keep it.**

### Narrative voice rule

All narrative content must read like fiction. A reader should never be able to tell this is a TTRPG session.

**Banned references:** "the session", "the GM", "the player", "the DM", dice rolls ("rolled a grim"), game mechanics (pools, checks, sparks, story points, grim results, assist dice, suspense spends), character arcs as a game concept, meta-session framing, how entities were established at the table, transient mechanical states, player-vs-character attribution, suggestions for future sessions.

**Translate mechanical outcomes into narrative.** Every game mechanic has a fictional counterpart — describe that instead. A failed healing roll becomes "his divine light faltered." A story point establishment becomes nothing — just state the fact.

### Entity recognition

1. If an entity name matches the known entities list → it's known. Record updates under `entity_updates`.
2. If a name is new, check the KB file contents list above:
   - **Direct match** → record as `entity_updates` for the parent entity. Include `parent_file` and `sub_section` fields.
   - **Semantically related** (e.g., "The Dark Harlequin" relates to "The Harlequins" in old-gods.md) → record as `entity_updates` for the parent entity. Note the related sub-section in the update.
3. If truly new and unrelated to any existing entry:
   - **NPCs:** Add to `new_entities` only if they have a relationship with a PC, are connected to a major NPC, had a substantive exchange with PCs, or are likely to recur. Otherwise, just name them in event descriptions. When uncertain, include them.
   - **Locations:** Add to `new_entities` only if standalone (not a sub-location), a recurring destination, or plot-critical. Sub-locations should be mentioned in event descriptions instead.
   - **Items/Factions:** Add if meaningfully introduced (described, used, or plot-relevant).
4. If ambiguous ("the old wizard"), add to `unresolved_references`.

### Rules clarifications

Include only when the GM was explicitly uncertain, said "let's rule it this way for now," or said they need to check the book later. Do NOT include confident rules explanations or character fiction establishment.

### Date extraction (chunk 0 only)

If this is chunk 0, extract the session date from the first timestamped line. Expected format: `[M/DD/YYYY H:MM AM/PM]`. Report it in `session_date` field as YYYY-MM-DD.

## Output format

Write a YAML file with exactly these fields:

```yaml
chunk_index: {chunk_index}
session_date: "YYYY-MM-DD"  # Only in chunk 0; omit from other chunks
chunk_summary: |
  2-3 sentence summary of what happens in this chunk. Narrative voice.
major_events:
  - description: |
      Narrative description of what happened.
    entities_involved: ["Name1", "Name2"]
    location: "Location Name"
new_entities:
  npcs:
    - name: "Name"
      description: "Description"
      first_location: "Location"
      notes: "Notes"
  locations:
    - name: "Name"
      type: "Settlement|Landmark|Region|etc"
      description: "Description"
      notes: "Notes"
  items:
    - name: "Name"
      description: "Description"
      current_holder: "Name"
  factions: []
entity_updates:
  - entity: "Known Entity Name"
    category: "pc|npc|location|item|faction|world"
    parent_file: "factions/old-gods.md"  # optional, for sub-entity updates
    sub_section: "The Harlequins"  # optional, which section it relates to
    new_info: |
      New information learned in this chunk.
questions_raised:
  - "Question text"
questions_resolved:
  - question: "Question text"
    answer: "Answer text"
arc_progress:
  - arc_name: "Arc Name"
    arc_type: "group|character"
    development: |
      What progressed in this chunk.
notable_quotes:
  - speaker: "Character Name"
    line: "The exact or near-exact quote"
    context: "Brief context"
rules_clarifications:
  - topic: "Topic"
    clarification: "What was ruled and why"
filtered_sections:
  - line_range: "start-end"
    reason: "Why this was filtered"
gm_observations:
  - "Observation about pacing, player engagement, etc."
unresolved_references:
  - reference: "the reference"
    context: "Where/how it appeared"
    likely_match: "Best guess"
    line_approx: "~line N"
```

Use empty lists `[]` for categories with no entries. Omit the `session_date` field entirely for chunks other than chunk 0.
````

### Step 4 — Consolidate

After all subagents complete, read all per-chunk result YAML files:
`inbox/transcripts/chunks/session-{N}-result-{i}.yaml` for i in 0..chunk_count-1.

Merge the results across all chunks:

1. **Extract date** — Use `session_date` from chunk 0's result (unless date was provided in arguments).

2. **Sequence events** — Concatenate `major_events` from all chunks in chunk order (they're already chronological within each chunk). Review for duplicate events that span chunk boundaries (due to overlap) — deduplicate, keeping the richer description.

3. **Deduplicate entities** — Same NPC/location/item appearing in multiple chunks? Merge to one entry with combined description and notes.

4. **Merge entity updates** — Same entity updated in multiple chunks? Combine `new_info` into one entry.

5. **Resolve cross-chunk references** — If "the old wizard" in chunk 1 becomes clearly identifiable as Garland by chunk 3, resolve it. Move resolved items from `unresolved_references` to the appropriate category. Flag truly ambiguous items in `unresolved_references`.

6. **Merge questions** — Concatenate and deduplicate `questions_raised` and `questions_resolved`.

7. **Merge arc progress** — Same arc updated in multiple chunks? Combine development text.

8. **Merge remaining lists** — Concatenate `notable_quotes`, `rules_clarifications`, `filtered_sections`, `gm_observations`, `unresolved_references`. Deduplicate where appropriate.

9. **Write summary** — Synthesize chunk summaries into a 2-4 paragraph narrative of the full session, written as fiction-style prose like a chapter summary in a novel. The narrative voice rule applies fully: no references to sessions, GMs, players, dice, game mechanics, or meta-activity. The summary should be substantive enough to serve as the session record — covering key scenes, character decisions, and how events concluded.

10. **Write recap teaser:**
    - **If provided by user:** use it directly as the `recap_teaser` value. Verify it follows narrative voice rules — flag to the user if it doesn't, but do NOT rewrite it.
    - **If not provided:** generate a dramatic 1-2 sentence hook for next session's opening.

### Step 5 — Write final YAML

Write the consolidated data to:

```
inbox/transcripts/extracted/session-{NUMBER}.yaml
```

Use the output format defined in the Output Format section below.

### Step 6 — Cleanup & report

Delete all chunk files and result files from `inbox/transcripts/chunks/` for this session:
```bash
rm inbox/transcripts/chunks/session-{N}-chunk-*.txt inbox/transcripts/chunks/session-{N}-result-*.yaml inbox/transcripts/chunks/session-{N}-manifest.json
```

Then report:

```
## Extraction Complete: session-{NUMBER}.yaml

**Transcript:** {path to prepared transcript}
**Chunks processed:** {n} (~{total lines} lines)

**Filtered out:**
- {n} non-game sections (~{n lines} lines total)
- See `filtered_sections` in YAML for details

**Extracted:**
- Major events: {n}
- New NPCs: {n} ({names})
- New locations: {n} ({names})
- New items: {n} ({names})
- Entity updates: {n} ({names})
- Questions raised: {n}
- Questions resolved: {n}
- Arc progress: {n} arcs updated
- Notable quotes: {n}
- Rules clarifications: {n}

**Unresolved references (for review):**
- {reference} (~line {n}) — {likely_match}
- ...

**Recap/teaser:** {provided by user | generated from transcript}

**Output:** inbox/transcripts/extracted/session-{NUMBER}.yaml

**Next step:** Review the YAML, then run incorporate-session
```

---

## Output Format

```yaml
session_number: 1
date_played: "2026-01-24"
source_transcript: "inbox/transcripts/prepared/session-1.txt"

recap_teaser: |
  When we last left our heroes, they had just discovered the seal
  and unwittingly released something ancient and terrible...

summary: |
  Multi-paragraph narrative summary written as fiction-style prose.
  One sentence per line for clean diffs.

major_events:
  - description: |
      Narrative description of what happened.
    entities_involved: ["Castor", "Roderic", "Edric", "Garland"]
    location: "Location Name"

new_entities:
  npcs:
    - name: "NPC Name"
      description: |
        Description of the NPC.
      first_location: "Location"
      notes: "Why this NPC is significant"

  locations:
    - name: "Location Name"
      type: "Settlement|Landmark|Region"
      description: |
        Description of the location.
      notes: "Additional notes"

  items:
    - name: "Item Name"
      description: "Description"
      current_holder: "Holder"

  factions: []

entity_updates:
  - entity: "Entity Name"
    category: "pc|npc|location|item|faction|world"
    parent_file: "factions/old-gods.md"  # optional, for sub-entity updates
    sub_section: "The Harlequins"  # optional, which section it relates to
    new_info: |
      New information learned this session.

questions_raised:
  - "Question text"

questions_resolved:
  - question: "Question text"
    answer: |
      Answer text.
    session_established: 1

arc_progress:
  - arc_name: "Arc Name"
    arc_type: "group|character"
    development: |
      What progressed this session.

notable_quotes:
  - speaker: "Character Name"
    line: "The exact or near-exact quote"
    context: "Brief context"

rules_clarifications:
  - topic: "Topic"
    clarification: |
      What was ruled and context.

filtered_sections:
  - line_range: "start-end"
    reason: "Why this was filtered"

gm_observations:
  - "Observation text"

unresolved_references:
  - reference: "the reference"
    context: "Where/how it appeared"
    likely_match: "Best guess"
    line_approx: "~line N"
```

---

## After Extraction

Review the YAML file before running incorporate-session:
- Check `filtered_sections` — anything important accidentally filtered?
- Check `unresolved_references` — can you clarify any?
- Check `new_entities` — correct categorization?

Then run:
```
/incorporate-session inbox/transcripts/extracted/session-{NUMBER}.yaml
```

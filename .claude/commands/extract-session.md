# Skill: Extract Session

**Purpose:** Filter non-game content and extract structured session data from a prepared transcript, producing a small YAML file that the `incorporate-session` skill can efficiently process.

**Input:** Session number (ingest pipeline runs automatically)

**Output:** A structured YAML file in `inbox/transcripts/extracted/`

**Architecture:** Single-pass extraction — the main agent reads the entire prepared transcript in one context and produces the structured YAML directly. A typical session transcript is ~40k–50k tokens, well within the available context window, so there is no chunking and no per-chunk subagents. Reading the whole transcript at once preserves cross-references, narrative arc, and scene continuity that chunked extraction used to fragment. The ingest pipeline still generates a manifest of pre-computed entity context (known entities, KB sub-entity headers, campaign context), which the main agent reads to ground entity recognition.

---

## Workflow

### Step 1 — Parse arguments

`$ARGUMENTS` format:
```
<session-number> [YYYY-MM-DD]
[optional recap/teaser text on subsequent lines]
```

- **First line:** session number (required) and optional date — sets `session_number` and `date_played` in the YAML output.
- **Subsequent lines (if any):** treated as a **provided recap/teaser**. This is GM-written prose that will be used as the `recap_teaser` value and as an authoritative reference for entity spelling during extraction.
- Date is optional — if omitted, it will be extracted from the transcript.
- If session number is missing, prompt the user and stop.

### Step 2 — Ingest transcript

Run the ingest pipeline to download and prepare the transcript (this also generates the manifest of entity context):

```bash
python3 scripts/ingest_transcript.py --session {session_number}
```

- If this succeeds, the prepared transcript (`inbox/transcripts/prepared/session-{N}.txt`) and the manifest (`inbox/transcripts/manifest/session-{N}-manifest.json`) both exist — proceed to Step 3.
- If it fails, report the error and stop. Common failure: missing `DISCORD_TOKEN` env var.
- If the transcript was already downloaded to a local file, pass it through:
  `python3 scripts/ingest_transcript.py --session {N} --input <path-to-raw-file>`

### Step 3 — Load context and the full transcript

Read `inbox/transcripts/manifest/session-{N}-manifest.json`. Use it for entity-grounding context. The fields:
- `session` — session number
- `source_transcript` — path to the prepared transcript (read this whole file in Step 4)
- `total_lines` — total line count
- `known_entities` — dict of entity names by category (pcs, npcs_and_others, locations, items, factions, world)
- `kb_filenames` — dict of KB filenames by subdirectory
- `sub_entity_map` — dict mapping sub-entity header names to `{"parent_file", "parent_name", "category"}` (e.g., `"The God of Ruin" → {"parent_file": "factions/old-gods.md", "parent_name": "Old Gods", "category": "factions"}`)
- `kb_content_hints` — dict mapping KB file paths to lists of sub-entity section names (e.g., `"factions/old-gods.md" → ["The God of Ruin", "The Harlequins", ...]`)
- `campaign_context` — contents of `exports/campaign-index.md` (empty string if file doesn't exist)

Also read `config/speaker-map.yaml` for the PC list and transcription corrections.

Then read the **entire prepared transcript** at the `source_transcript` path. Read the whole file — do not sample or skim. If the transcript is unusually large (well beyond ~150k tokens / ~600k characters), note that to the user but proceed; it still fits in context.

### Step 4 — Extract in a single pass

Read the full transcript and produce the consolidated structured data directly, applying all the rules below. Because you see the entire session at once, resolve references, track entities, and shape the narrative across the whole transcript — there is no per-chunk fragmentation to reconcile.

#### Player characters

The PCs are listed in `config/speaker-map.yaml`. Treat anyone listed there as a player character (goes in `kb/pcs/`), everyone else as an NPC.

#### Transcription corrections

`config/speaker-map.yaml` lists known speech-to-text errors as `match` → `replace` pairs. When you see the "match" text, the correct word is the "replace" text. Apply these when reading the transcript.

#### Known entities

The manifest's `known_entities` and `kb_filenames` list entities that already exist in the knowledge base. If you see them mentioned, record updates under `entity_updates`, NOT under `new_entities`.

#### Sub-entities (manifest `sub_entity_map` / `kb_content_hints`)

These section headers exist inside KB files and represent sub-entries within larger entries. If you encounter these names OR closely related names in the transcript, record them as `entity_updates` for the parent entity — NOT as `new_entities`. Include the `parent_file` and `sub_section` fields on the update.

#### Provided recap/teaser (if any)

If the user provided recap/teaser text in the arguments, treat entity spellings in that text as authoritative — they override STT spellings from the transcript when there's a conflict.

### Extraction rules

#### What to filter out (log to `filtered_sections`)

- Real-world chit-chat unrelated to the game
- AFK breaks ("getting water", "bathroom break")
- Technical issues ("can you hear me?", "Discord is lagging")
- Scheduling talk ("same time next week?")
- Extended off-topic tangents (TV shows, news, personal stories)

#### What to keep (game-related)

- In-character dialogue and narration
- Rules discussions and clarifications
- Character ability discussions
- World-building discussion
- Dice roll announcements and results
- Session planning within the game context
- Jokes/banter that reference game content

**When uncertain, keep it.**

#### Narrative voice rule

All narrative content must read like fiction. A reader should never be able to tell this is a TTRPG session.

**Banned references:** "the session", "the GM", "the player", "the DM", dice rolls ("rolled a grim"), game mechanics (pools, checks, sparks, story points, grim results, assist dice, suspense spends), character arcs as a game concept, meta-session framing, how entities were established at the table, transient mechanical states, player-vs-character attribution, suggestions for future sessions.

**Translate mechanical outcomes into narrative.** Every game mechanic has a fictional counterpart — describe that instead. A failed healing roll becomes "his divine light faltered." A story point establishment becomes nothing — just state the fact.

#### Entity recognition

1. If an entity name matches the known entities list → it's known. Record updates under `entity_updates`.
2. If a name is new, check the sub-entity context above:
   - **Direct match** → record as `entity_updates` for the parent entity. Include `parent_file` and `sub_section` fields.
   - **Semantically related** (e.g., "The Dark Harlequin" relates to "The Harlequins" in old-gods.md) → record as `entity_updates` for the parent entity. Note the related sub-section in the update.
3. If truly new and unrelated to any existing entry:
   - **NPCs:** Add to `new_entities` only if they have a relationship with a PC, are connected to a major NPC, had a substantive exchange with PCs, or are likely to recur. Otherwise, just name them in event descriptions. When uncertain, include them.
   - **Locations:** Add to `new_entities` only if standalone (not a sub-location), a recurring destination, or plot-critical. Sub-locations should be mentioned in event descriptions instead.
   - **Items/Factions:** Add if meaningfully introduced (described, used, or plot-relevant).
4. If ambiguous ("the old wizard"), try to resolve it from the rest of the transcript first. If it becomes clearly identifiable (e.g., "the old wizard" in an early scene is plainly Garland by a later scene), resolve it to that entity. Only if it remains genuinely ambiguous after reading the whole session, add it to `unresolved_references`.

#### Rules clarifications

Include only when the GM was explicitly uncertain, said "let's rule it this way for now," or said they need to check the book later. Do NOT include confident rules explanations or character fiction establishment.

#### Favors

A **Favor** is a Chasing Adventure GM move: a bond of obligation between a character and another party (PC or NPC). It is **gained** via **Gratify** (a character does someone a service or compels them, earning a debt), **spent** via **Appease** (cashing the favor in to get cooperation) or **Refuse** (calling on the favor but being turned down), and **lost** via **Antagonize** (the bond is broken by mistreatment or betrayal).

Record a `favors:` entry whenever a character:
- **Favors** another character or swears an obligation to them (`move: gratify`, `status: active`);
- **cashes one in** — calls on an existing favor for cooperation (`move: appease`) or is refused (`move: refuse`);
- **breaks one** through mistreatment or betrayal (`move: antagonize`, `status: lost`);
- **reveals** a favor that already existed (`move: reveal`) — see below.

For each entry capture the in-fiction `event` (the real moment, one sentence per line, narrative voice — never name the move "in the fiction"), any `sworn` promise, the `move`, and the resulting `status` (active | spent | lost | open). Set `favorer` to the one who owes / feels the obligation, `favored` to the one owed, and `pc_anchor` to the PC whose page the favor lands on. When a party is unnamed (e.g. "a companion the Light has already burned"), use a short description in place of the name and set `status: open` so it can be resolved later.

**Revealed favors (Connect and other play-to-find-out moves).** A favor is sometimes not *created* in play but *uncovered* — a Connect move (or similar backstory declaration) establishes that an NPC, the relationship, AND a favor between them were all already true. The favor did not begin in this session; the table merely learned of it. Record these with `move: reveal`, set `session_established` to when the bond actually formed (a prior session number, or "pre-campaign" / omit if it predates play or is unknown), and describe the surfacing scene in `event`. Do **not** tag a revealed favor as `gratify`, and do not let the fiction imply this session's events incurred the debt. The incorporated annotation uses the origin (e.g. "Pre-campaign") in place of a favor-move, mirroring an open backstory favor.

Favors are captured **both** structurally here (so the mechanic is tracked on purpose) **and** as fiction in the `summary` and any relevant `entity_updates` (so the bond reads as story). Do not let the structural capture replace the narrative.

#### Entity update scope

Entity updates should contain only **durable facts** that would belong on the entity's wiki page and matter beyond this session. Think of it as updating a reference card, not narrating what happened.

**Include in entity_updates:**
- New relationships, contacts, or affiliations established
- Abilities, constraints, or ongoing conditions (especially new limitations or unlocked powers)
- Backstory or lore revelations about the entity
- Drives, motivations, or character traits revealed
- Architectural details, lore, or structural facts about locations
- Faction structure, theology, or organizational information
- Durable status changes that persist until explicitly resolved (e.g., "is now wanted", "lost access to beaver form", "has been imprisoned") — as distinct from in-progress situations like "soldiers are approaching" or "camped outside the walls"

**Do NOT include in entity_updates (use major_events instead or omit):**
- Combat actions or tactical choices already described in major_events
- Temporary states that resolve within the session (captured then freed, fought then won)
- Transient situational facts that will resolve in the next session or two — in-progress threats ("preparing to arrest him"), temporary positioning ("has made camp outside the walls"), and cliffhanger states. These belong in major_events or the session summary. The test: is this a *status change* (durable until explicitly resolved) or a *situation in progress* (will naturally resolve as events continue)?
- Session-specific behavior ("remained hidden", "chose to ignore a fleeing prisoner")
- Information already captured in a major_event, another entity's update, or a location/faction entry
- Environmental observations that belong in a location entry, not a character entry
- Blow-by-blow action sequences — summarize the lasting consequence, not the play-by-play

**Test:** Would a reader preparing for the *next* session need this on the entity's reference page? If it only matters for understanding *this* session's story, it belongs in major_events or the summary, not entity_updates.

After drafting entity updates, triage each one:
- **Keep** items that are durable reference facts (new contacts, abilities, constraints, lore, drives, faction info).
- **Drop** items that are session-specific actions already covered by major_events, temporary states, or blow-by-blow combat details.
- **Promote to major_event** any item that describes a significant plot moment rather than a durable fact (e.g., "used Eyes of the Faithful to confirm Severin's sincerity" is a plot event, not a wiki fact — though its *consequence* like "now trusts Severin" could remain as an entity update).

#### Date extraction

If a date was not provided in the arguments, extract the session date from the first timestamped line of the prepared transcript. Expected format: `[M/DD/YYYY H:MM AM/PM]`. Report it as YYYY-MM-DD in `date_played`.

### Step 5 — Compose the summary and recap teaser

**Summary:** Write a 2-4 paragraph narrative of the full session, as fiction-style prose like a chapter summary in a novel. The narrative voice rule applies fully: no references to sessions, GMs, players, dice, game mechanics, or meta-activity. The summary should be substantive enough to serve as the session record — covering key scenes, character decisions, and how events concluded. Because you have read the entire transcript, the summary should reflect the true arc of the session from open to close.

**Recap teaser:**
- **If provided by user:** use it directly as the `recap_teaser` value. Verify it follows narrative voice rules — flag to the user if it doesn't, but do NOT rewrite it.
- **If not provided:** generate a dramatic 1-2 sentence hook for next session's opening.

### Step 6 — Write final YAML

Write the consolidated data to:

```
inbox/transcripts/extracted/session-{NUMBER}.yaml
```

Use the output format defined in the Output Format section below. Use empty lists `[]` for categories with no entries.

### Step 7 — Cleanup & report

Delete the transient manifest for this session:
```bash
rm -f inbox/transcripts/manifest/session-{N}-manifest.json
```

Then report:

```
## Extraction Complete: session-{NUMBER}.yaml

**Transcript:** {path to prepared transcript}
**Lines processed:** {total_lines}

**Filtered out:**
- {n} non-game sections
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
- Favors: {n}

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

favors:
  - move: "gratify"            # gratify | appease | refuse | antagonize | reveal
    favorer: "Garland yn Greenholt"   # the one who owes / feels the obligation
    favored: "Sergeant Iyer"          # the one owed (PC or NPC; description if unnamed)
    pc_anchor: "Garland yn Greenholt" # the PC whose page this lands on
    event: |
      The real, in-fiction moment that created, revealed, or changed the favor (one sentence per line).
    sworn: |
      What was promised, if anything. Omit if none.
    session_established: 6     # session the favor ORIGINATED — for a `reveal` this is when the
                               # bond actually formed (often before play): use the prior session
                               # number, or "pre-campaign" / omit if it predates play / is unknown.
                               # NOT the session it surfaced in (that goes in `event`).
    status: "active"           # active | spent | lost | open

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

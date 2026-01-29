# Skill: Extract Session

**Purpose:** Filter non-game content and extract structured session data from a prepared transcript, producing a small YAML file that the `incorporate-session` skill can efficiently process.

**Input:** A prepared transcript from `inbox/transcripts/prepared/`

**Output:** A structured YAML file in `inbox/transcripts/extracted/`

---

## Workflow

### Step 1 — Parse arguments & discover transcript

`$ARGUMENTS` format: `<session-number> [YYYY-MM-DD]`

- Session number is required — sets `session_number` in the YAML output.
- Date is optional — if omitted, extract from the first timestamped line in the transcript (expected format: `[M/DD/YYYY H:MM AM/PM]`).
- If session number is missing, prompt the user and stop.

List files in `inbox/transcripts/prepared/`.
Exclude `.gitkeep`.
If no prepared transcripts exist, report that and stop.
If multiple prepared transcripts exist, ask the user which one to process.

### Step 2 — Load context (minimal)

Load only what is needed for entity recognition:

| Resource | Action |
|----------|--------|
| `config/speaker-map.yaml` | Read in full (identifies PCs) |
| `config/entity-aliases.yaml` | Read in full (resolves known entities) |
| KB directories (`grimwild-kb/pcs/`, `npcs/`, `locations/`, `items/`, `factions/`, `sessions/`, `story-arcs/`, `world/`) | **List filenames only** — do NOT read file contents |

This gives you a lookup table of known entities without consuming context.

### Step 3 — First pass: scan for structure

Read the first ~2000 lines to understand session scope:

- Identify the session date from timestamps (if not provided in arguments).
- Note major scene breaks (location changes, "okay so...", combat starts/ends).
- Build initial entity mention list.
- Identify the recap if one was given at session start.
- Note obvious non-game sections to skip.

### Step 4 — Scene-by-scene extraction with filtering

Process the transcript in chunks of ~1500-2000 lines, overlapping slightly at boundaries to avoid missing context.

**For each chunk, first filter:**

Skip and log non-game content:
- Real-world chit-chat (ice machines, TV shows, personal anecdotes unrelated to game)
- AFK announcements and waiting chatter ("I'm going to get water", "be right back")
- Technical issues (Discord problems, audio issues, "can you hear me?")
- Scheduling discussion

**Keep as game-related (do NOT filter):**
- In-character dialogue and narration
- Rules discussions and clarifications
- Character ability discussions
- World-building discussion
- Dice roll announcements and results
- Session planning within the game context
- Jokes/banter that reference game content

**When uncertain, keep it** — better to extract something marginal than miss something important.

**Then extract and accumulate from game-related content:**

| Category | What to Look For |
|----------|------------------|
| **Events** | Combat, discoveries, decisions, travel, conversations with NPCs. Descriptions must follow the narrative voice rule — describe what happened in the story, not what happened at the table. |
| **New entities** | Names not in your known-entity list (NPCs, locations, items, factions) |
| **Entity updates** | New information about known PCs/NPCs |
| **Questions raised** | Mysteries introduced, hooks planted, unanswered questions |
| **Questions answered** | Previously open questions that got resolved |
| **Arc progress** | Developments in ongoing story arcs |
| **Notable quotes** | Memorable lines worth preserving |
| **Rules clarifications** | GM rulings made when uncertain — things to verify later |
| **Unresolved references** | Entity mentions you can't confidently match |
| **Filtered sections** | Log line ranges and reasons for skipped content |

**Accumulation strategy:**
- Maintain running lists for each category.
- When you find the same entity in multiple chunks, merge the information.
- When you find the same event described differently, consolidate to one entry.

**Narrative voice rule — all narrative content must read like fiction:**

This rule applies to **every narrative field** in the YAML: `summary`, `recap_teaser`, `major_events` descriptions, `description`, `notes`, `new_info`, `development`, `context`, `answer`, and any other field that describes what happened or what exists in the world.

A reader should never be able to tell this is a tabletop RPG session. Write as if recounting events in a novel.

**Explicitly banned references:**
- "The session", "this session", "the session opened/ended"
- "The GM", "the player", "the DM", any real-person attribution
- Dice rolls ("rolled a grim", "rolled a perfect presence check", "failed a check")
- Game mechanics: pools, checks, sparks, story points, grim results, assist dice, suspense spends, backgrounds as a game concept
- Character arcs as a game concept ("His character arc is 'uncover the truth'")
- Meta-session framing ("The session opened with a world-building recap", "The GM delivered an exposition drop")
- How entities were established at the table ("Named by Edric during play", "Story point spent by Garland", "established by Garland via story point")
- Transient mechanical states ("pool exhausted until next session", "spell slots spent")
- Player-vs-character attribution ("Jay decided...", "Ken established...")
- Suggestions for future sessions or system changes

**Translate mechanical outcomes into narrative.** Every game mechanic has a fictional counterpart — describe that instead:

| BAD (mechanical) | GOOD (narrative) |
|---|---|
| "Roderic's healing pool failed catastrophically — the ruin's proximity caused the horses to wither" | "Roderic called upon Lucifer's light to heal the exhausted horses, but the ruin's proximity overwhelmed his divine power — the horses withered before his eyes" |
| "Edric rolled a perfect presence check and determined that Aldric appears uninvolved" | "Edric's charm proved irresistible — he plied the guards with drinks and conversation, and came away convinced Aldric is uninvolved" |
| "(established by Garland via story point)" | *(omit entirely — the thing exists, that's all)* |
| "The session opened with a world-building recap establishing the geography" | *(omit meta framing entirely; start with what happened in the story)* |

### Step 5 — Consolidation

After processing all chunks:

1. **Deduplicate entities** — Same NPC mentioned in chunks 2 and 5? Merge to one entry.
2. **Resolve obvious references** — "the paladin" in context clearly referring to Roderic? Map it.
3. **Flag ambiguous references** — Can't tell if "the old wizard" is Garland or someone new? Add to `unresolved_references`.
4. **Sequence events** — Order `major_events` chronologically as they occurred in session.
5. **Write summary** — Synthesize a 2-3 paragraph narrative of what happened, written as fiction-style prose — like a chapter summary in a novel. The narrative voice rule applies fully here: no references to sessions, GMs, players, dice, game mechanics, or meta-activity. Translate every mechanical outcome into its narrative equivalent (a failed healing roll becomes "his divine light faltered"; a story point establishment becomes nothing — just state the fact as if it always existed). A reader should never be able to tell this is a tabletop RPG session. The summary is passed directly into the session file, so it needs to be substantive enough to serve as the session record — covering key scenes, character decisions, and how events concluded.
6. **Write recap teaser** — A dramatic 1-2 sentence hook for next session's opening.

### Step 6 — Write YAML output

Write the consolidated data to:

```
inbox/transcripts/extracted/session-{NUMBER}.yaml
```

Use the output format defined in the Output Format section below.

### Step 7 — Report summary

After extraction completes, report:

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

**Output:** inbox/transcripts/extracted/session-{NUMBER}.yaml ({n} tokens)

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
  The party traveled down the river toward the beaver dam, following
  reports of corruption spreading through the waterways. Along the way,
  they encountered a pack of dire coyotes near the old mill — the animals
  were unnaturally aggressive, likely maddened by the tainted water. After
  a sharp fight, the party pressed on, battered but determined.

  At the riverbank, Castor shifted into beaver form and communicated with
  the local colony through tail-slaps and gestures. The beavers confirmed
  what the party feared: something wrong was moving downstream, fouling
  the water and weakening the dam's foundations. Castor convinced the
  colony to begin emergency repairs while the party raced ahead to
  intercept the corruption at its source.

  The session ended with the party pushing hard toward the dam, knowing
  that if the corruption reaches it before they do, the entire Ashen Vale
  downstream will be exposed.

major_events:
  - description: "Combat with dire coyotes near the mill"
    entities_involved: ["Castor", "Roderic", "Edric", "Garland"]
    location: "Old Mill"

  - description: "Discovered corruption racing toward beaver dam"
    entities_involved: ["Castor"]
    location: "River"

new_entities:
  npcs:
    - name: "Farmer Wilkins"
      description: "Gruff farmer who warned party about strange things in the river"
      first_location: "Near the mill"
      notes: "Seemed frightened, mentioned 'the old wizard' who used to live nearby"

  locations:
    - name: "The Beaver Dam"
      type: "Landmark"
      description: "Large dam downstream, home to a beaver colony Castor knows"

  items:
    - name: "Coyote Fang Necklace"
      description: "Necklace of dire coyote fangs taken as trophy"
      current_holder: "Edric"

  factions: []

entity_updates:
  - entity: "Castor"
    category: "pc"
    new_info: |
      Can communicate with beavers through gestures and body language.
      Not verbal speech, but understands them from years of living as a beaver.
      The beaver colony downstream knows him and trusts him.

  - entity: "Sir Roderic"
    category: "pc"
    new_info: |
      Used healing pool to restore Garland after coyote attack.

questions_raised:
  - "What is the source of the corruption in the river?"
  - "Will the beaver dam hold against the approaching corruption?"

questions_resolved:
  - question: "Can Castor speak with animals?"
    answer: "Not verbally, but can communicate with beavers through gestures and body language developed over years as a beaver"
    session_established: 1

arc_progress:
  - arc_name: "Heralds of Ruin"
    arc_type: "group"
    development: |
      The corruption spreading down the river appears connected to
      releasing the God of Ruin. The party is beginning to see
      consequences of their actions at the seal.

  - arc_name: "Castor's Curse"
    arc_type: "character"
    development: |
      Castor's connection to the beaver colony deepened. His ability
      to communicate with them proved crucial. Still unclear if this
      is remnant of the curse or something else.

notable_quotes:
  - speaker: "Edric"
    line: "I've seen that look in a river before. It's not water anymore."
    context: "Observing the corruption in the water"

  - speaker: "Castor"
    line: "They're scared. The whole colony. Something's coming."
    context: "After communicating with the beavers"

rules_clarifications:
  # GM rulings made when uncertain — verify these against the rulebook later
  - topic: "Can you push yourself twice on the same roll?"
    ruling: "Ruled NO for this session — one push per roll"
    ruling_context: "Player asked, I wasn't sure, made a call to keep moving"

  - topic: "Does armor reduce damage from falling?"
    ruling: "Ruled YES — armor absorbs first hit of any damage type"
    ruling_context: "Ambiguous in rules — check if this is RAW or house rule"

filtered_sections:
  - line_range: "847-862"
    reason: "AFK break — GM getting water, chit-chat about ice machines"
  - line_range: "2103-2115"
    reason: "Technical discussion — Discord audio issues"

gm_observations:
  - "Combat pacing felt good - 3 rounds was right length"
  - "Players engaged well with the corruption mystery"
  - "Consider: what happens if dam breaks?"

unresolved_references:
  - reference: "the old wizard"
    context: "Farmer Wilkins mentioned 'the old wizard who used to live at the mill'"
    likely_match: "Garland? Or unknown NPC?"
    line_approx: "~line 1200"

  - reference: "the Shepherd's Teeth"
    context: "Castor mentioned the beavers avoid 'the Shepherd's Teeth upstream'"
    likely_match: "Witch Stones? New location?"
    line_approx: "~line 2400"
```

---

## Entity Recognition Logic

For each potential entity name mentioned in the transcript:

1. **Check `speaker-map.yaml`** — If found under a player's `characters:` list, it's a PC. Record updates under `entity_updates` with `category: "pc"`.

2. **Check `entity-aliases.yaml`** — If found, resolve to canonical name. Record updates under `entity_updates`.

3. **Check KB directory filenames** (slugified match) — "Ashen Vale" matches `ashen-vale.md`? It's known. Record updates.

4. **If no match found:**
   - If ambiguous ("the old wizard", "the Shepherd's Teeth"), add to `unresolved_references`.
   - For **locations**: apply the Location Significance Test below. For **items and factions**: add to `new_entities` if meaningfully introduced (described, visited, used, or plot-relevant).
   - For **NPCs**: apply the NPC Significance Test below before adding to `new_entities`.

### NPC Significance Test

Not every named NPC warrants a KB entry. Some are **set dressing** — they have names because it would be awkward to call them "the merchant," but they exist to serve a single story beat and won't recur. These NPCs should be named in `major_events` descriptions where they appear, but do NOT add them to `new_entities`.

Add an NPC to `new_entities` if they meet **any** of these criteria:

- **Relationship with a PC** — Personal, familial, professional, or antagonistic connection to a player character (e.g., a PC's grandchild, a PC's rival)
- **Connected to a major NPC** — Serves, reports to, or is related to a named NPC already in the KB (e.g., a count's sergeant-at-arms, a villain's lieutenant)
- **Substantive exchange** — Had a meaningful interaction with PCs beyond a simple transaction — information was exchanged, conflict arose, or the NPC made decisions that affected the story
- **Likely to recur** — The narrative sets up reasons for the party to encounter this NPC again (they live somewhere the party will return, they have unfinished business, the GM invested detail in them)

**When uncertain, include the NPC** — it's easier for the reviewer to remove an entry than to notice one is missing. Flag borderline cases with a note in the NPC's `notes` field.

**Set dressing examples** (do NOT add to `new_entities`):
- A merchant the party buys supplies from, with no ongoing relationship
- A townsperson who makes a one-off accusation resolved in the same scene
- A guard who gives directions and is never seen again

**Significant NPC examples** (DO add to `new_entities`):
- A guard sergeant connected to a major NPC's household, who had a substantive interaction with PCs and is stationed where the party may return
- A child with a personal relationship to a PC, introduced by the GM with detail and narrative weight

### Location Significance Test

Not every named place warrants its own KB entry. Some are **sub-locations** — a named feature within a larger, more notable location. Sub-locations should be folded into the parent location's `description` or `notes` field rather than getting a separate entry.

A location gets its **own** `new_entities` entry if it meets **any** of these criteria:

- **Standalone significance** — The location is a distinct place the party travels to, not a feature within another location (a town, a dungeon, a region)
- **Recurring destination** — The party is likely to return to this specific spot, or it's referenced as a destination in its own right
- **Plot-critical** — The location is central to a story arc or mystery (a sealed tomb, a faction headquarters)

If a location fails all three criteria, fold it into the parent location's `description` or `notes` field.

**Sub-location examples** (fold into parent):
- An abandoned hut on a lakeshore → describe within the lake's entry
- A specific room in a dungeon → describe within the dungeon's entry
- A campsite along a trail → mention in the trail or region's entry

**Standalone examples** (DO add to `new_entities`):
- A town the party visits and interacts with people in
- A dam that is central to a story arc
- A dungeon the party enters and explores

---

## Classification Rules

### DO Extract (Game-Related)

- In-character dialogue and narration
- Plot developments and story beats
- Character moments (growth, decisions, relationships)
- World-building details revealed in play
- Rules clarifications where the GM was uncertain and made a ruling to verify later
- Combat outcomes and consequences
- NPC interactions and new NPCs introduced
- Location descriptions and new locations visited
- Items found, used, or significant
- Questions raised by the narrative
- Answers to previously open questions
- Memorable quotes
- Jokes/banter that reference game content (often reveals character dynamics)

### DO Filter Out (Non-Game) — Log to `filtered_sections`

- Real-world chit-chat unrelated to the game
- AFK breaks ("getting water", "bathroom break")
- Technical issues ("can you hear me?", "Discord is lagging")
- Scheduling talk ("same time next week?")
- Extended off-topic tangents (TV shows, news, personal stories)

### Edge Cases — When Uncertain, KEEP IT

- Rules discussion that seems tangential → Keep (may establish precedent)
- Joke that might reference game content → Keep (often does)
- Brief personal aside mid-scene → Keep (context matters)

The `filtered_sections` log gives visibility. If something is missing from the extraction, the user can check the prepared transcript and re-extract.

---

## Edge Cases

**Very long sessions (4+ hours):**
More chunks, same approach. May need more consolidation to avoid bloated YAML. Focus on major beats; minor details can be trimmed.

**Multiple combats:**
Each significant combat is one `major_event`. Don't enumerate every round; summarize outcome and consequences.

**Time jumps within session:**
Note in event descriptions ("later that day...", "the next morning..."). Keep events in session-chronological order.

**Flashbacks or stories-within-stories:**
If a character tells a story about the past, extract relevant lore to `entity_updates` or `new_entities`. Note the framing ("Garland recounted that...").

**Unclear new vs. existing entity:**
When genuinely uncertain, add to `unresolved_references`. The human reviewer will clarify.

**Rules discussion:**
- If GM was uncertain and made a ruling → `rules_clarifications` (needs verification)
- If GM confidently explained a rule → Do not extract (just teaching)
- If establishing character fiction → `entity_updates` (narrative, not rules)

**Distinguishing rules content:**

| Content Type | Where It Goes | Example |
|--------------|---------------|---------|
| **Uncertain ruling** | `rules_clarifications` | "I ruled you can't push twice, but I need to check that" |
| **Rules explanation** | Filter out (not extracted) | GM explaining how power pools work to players |
| **Fiction establishment** | `entity_updates` | "Castor's forms all have beaver traits" |

**Include in `rules_clarifications` only when:**
- The GM explicitly said they weren't sure
- The GM said "let's rule it this way for now"
- The GM said they need to check the book later
- A rule was ambiguous and the GM made a judgment call

**Do NOT include:**
- Rules the GM explained confidently
- Character fiction being established (even if discussed OOC)
- Mechanics working as documented

It's fine for this section to be empty if no uncertain rulings were made.

**Speech-to-text quality:**
Interpret intent, not literal garbled text. Use surrounding context to reconstruct meaning from fragmented STT output. Check `config/speaker-map.yaml` `transcription_corrections` for known errors.

**Entity mentioned but not introduced:**
If an entity is only mentioned in passing (e.g., "I heard about the Black Tower once"), do not add it to `new_entities`. Passing mentions can go to `unresolved_references` if they might matter later. For NPCs that are introduced but appear to be set dressing, see the NPC Significance Test in the Entity Recognition Logic section — name them in `major_events` but do not create entity entries.

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

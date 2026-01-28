# Skill: Extract Session

**Purpose:** Filter non-game content and extract structured session data from a prepared transcript, processing in chunks to manage context size. This skill transforms a large transcript (50k-100k+ tokens) into a small structured YAML file (~1-2k tokens) that the `incorporate-session` skill can efficiently process.

---

## Pipeline Position

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TRANSCRIPT PROCESSING PIPELINE                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. DOWNLOAD              2. PREPARE              3. EXTRACT                │
│  ───────────              ──────────              ──────────                │
│  Discord → raw/           raw/ → prepared/        prepared/ → extracted/   │
│                                                                             │
│  (script)                 (script)                (THIS SKILL)              │
│  download_transcript.py   process_transcript.py   extract-session           │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  4. INCORPORATE           5. DONE                                           │
│  ──────────────           ───────                                           │
│  extracted/ → KB files    transcript moved to processed/                    │
│                                                                             │
│  (skill)                                                                    │
│  incorporate-session                                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**This skill's role:** Filter out non-game content AND transform prepared transcript → structured YAML, enabling context-efficient KB incorporation.

---

## Input

- A prepared transcript from `inbox/transcripts/prepared/`
- Session number (extracted from filename or provided)

## Output

- A structured YAML file: `inbox/transcripts/extracted/session-{NUMBER}-extracted.yaml`

---

## Why This Skill Exists

Transcripts from voice sessions can be 50,000-100,000+ tokens. Loading a full transcript plus KB files plus templates exceeds context limits and degrades LLM performance.

This skill solves the problem by:
1. Reading the transcript in manageable chunks
2. Filtering out non-game chatter during processing
3. Extracting structured information from game-relevant content
4. Accumulating and consolidating findings
5. Outputting a small YAML file that contains everything needed for KB incorporation

The downstream `incorporate-session` skill then works with ~1-2k tokens instead of 50k+.

---

## Output Format

```yaml
session_number: 1
date_played: "2026-01-24"

recap_teaser: |
  When we last left our heroes, they had just discovered the seal
  and unwittingly released something ancient and terrible...

summary: |
  The party traveled down the river toward the beaver dam.
  They encountered dire coyotes near the old mill and fought them off.
  Castor communicated with local beavers to learn about corruption
  spreading downstream toward the dam.
  The session ended with the party racing to warn the beaver colony.

major_events:
  - description: "Combat with dire coyotes near the mill"
    entities_involved: ["Castor", "Roderic", "Edric", "Garland"]
    location: "Old Mill"
    
  - description: "Discovered corruption racing toward beaver dam"
    entities_involved: ["Castor"]
    location: "River"
    
  - description: "Castor communicated with beaver scouts"
    entities_involved: ["Castor"]
    location: "Riverbank"

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
      
    - name: "Old Mill"
      type: "Building" 
      description: "Abandoned mill along the river, site of dire coyote attack"
      notes: "In disrepair, mentioned as former home of 'the old wizard'"
      
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
      Pool is now exhausted until next session.
      
  - entity: "Garland"
    category: "pc"
    new_info: |
      Took significant damage in the coyote fight.
      Mentioned feeling "too old for this" afterward.

questions_raised:
  - "What is the source of the corruption in the river?"
  - "Will the beaver dam hold against the approaching corruption?"
  - "Who or what released the corruption upstream?"
  - "Who was 'the old wizard' Farmer Wilkins mentioned?"

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
    
  - speaker: "Garland"
    line: "I'm too old for diving out of the way of teeth."
    context: "After the coyote fight"

rules_clarifications:
  - topic: "Castor's animal communication"
    clarification: "Not magical speech - behavioral/gestural from years as a beaver. Works with beavers; unclear if extends to other animals."
    
  - topic: "Healing pool recovery"
    clarification: "Roderic's healing pool returns at start of next session, not after a rest."

filtered_sections:
  # Non-game content that was skipped during extraction
  # Included here for transparency — review if something seems missing
  - line_range: "847-862"
    reason: "AFK break — GM getting water, chit-chat about ice machines"
  - line_range: "2103-2115"
    reason: "Technical discussion — Discord audio issues"
  - line_range: "3521-3548"
    reason: "Off-topic — discussion about a TV show"

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

## Chunked Processing Approach

### Step 1: Load Context (Minimal)

Load only what's needed for entity recognition:

| Resource | Action |
|----------|--------|
| `config/speaker-map.yaml` | Read in full (identifies PCs) |
| `config/entity-aliases.yaml` | Read in full (resolves known entities) |
| KB directories | **List filenames only** — do NOT read file contents |

This gives you a lookup table of known entities without consuming context.

### Step 2: First Pass — Scan for Structure

Read the first ~2000 lines to understand session scope:

- Identify the session date/number from context or filename
- Note major scene breaks (location changes, "okay so...", combat starts/ends)
- Build initial entity mention list
- Identify the recap if one was given at session start
- Note any obvious non-game sections to skip

### Step 3: Scene-by-Scene Extraction (with Filtering)

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
| **Events** | Combat, discoveries, decisions, travel, conversations with NPCs |
| **New entities** | Names not in your known-entity list (NPCs, locations, items, factions) |
| **Entity updates** | New information about known PCs/NPCs |
| **Questions raised** | Mysteries introduced, hooks planted, unanswered questions |
| **Questions answered** | Previously open questions that got resolved |
| **Arc progress** | Developments in ongoing story arcs |
| **Notable quotes** | Memorable lines worth preserving |
| **Rules clarifications** | OOC discussion that establishes how something works |
| **Unresolved references** | Entity mentions you can't confidently match |
| **Filtered sections** | Log line ranges and reasons for skipped content |

**Accumulation strategy:**
- Maintain running lists for each category
- When you find the same entity in multiple chunks, merge the information
- When you find the same event described differently, consolidate to one entry

### Step 4: Consolidation

After processing all chunks:

1. **Deduplicate entities** — Same NPC mentioned in chunks 2 and 5? Merge to one entry.
2. **Resolve obvious references** — "the paladin" in context clearly referring to Roderic? Map it.
3. **Flag ambiguous references** — Can't tell if "the old wizard" is Garland or someone new? Add to `unresolved_references`.
4. **Sequence events** — Order `major_events` chronologically as they occurred in session.
5. **Write summary** — Synthesize the session into 3-5 sentences capturing the main arc.

### Step 5: Output YAML

Write the consolidated data to `inbox/transcripts/extracted/session-{NUMBER}-extracted.yaml`.

---

## Entity Recognition Logic

```
For each potential entity name mentioned in transcript:

1. Check speaker-map.yaml
   → If found under a player's characters: it's a PC, record updates
   
2. Check entity-aliases.yaml  
   → If found: resolve to canonical name, record updates
   
3. Check KB directory filenames (slugified match)
   → "Ashen Vale" matches ashen-vale.md? It's known, record updates
   
4. If no match found:
   → Likely a new entity OR an unresolved reference
   → If context makes it clear (introduced with description): new entity
   → If ambiguous ("the old wizard"): add to unresolved_references
```

---

## What to Extract vs. What to Filter

### DO Extract (Game-Related)

- In-character dialogue and narration
- Plot developments and story beats
- Character moments (growth, decisions, relationships)
- World-building details revealed in play
- Rules clarifications that establish "how things work"
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

The `filtered_sections` log gives you visibility. If you notice something missing from the extraction, you can check if it was filtered and recover from the prepared transcript.

---

## Handling Edge Cases

**Very long sessions (4+ hours):**
- More chunks, same approach
- May need more consolidation to avoid bloated YAML
- Focus on major beats; minor details can be trimmed

**Multiple combats:**
- Each significant combat is one `major_event`
- Don't enumerate every round; summarize outcome and consequences

**Time jumps within session:**
- Note in event descriptions ("later that day...", "the next morning...")
- Keep events in session-chronological order

**Flashbacks or stories-within-stories:**
- If a character tells a story about the past, extract relevant lore to `entity_updates` or `new_entities`
- Note the framing ("Garland recounted that...")

**Unclear new vs. existing entity:**
- When genuinely uncertain, add to `unresolved_references`
- The human reviewer will clarify

**Rules discussion that changes understanding:**
- Capture in `rules_clarifications`
- These inform how abilities/mechanics work going forward

---

## Report Format

After extraction completes, report:

```
## Extraction Complete: session-01-extracted.yaml

**Transcript:** inbox/transcripts/prepared/session-2026-01-24-prepared.txt
**Chunks processed:** 6 (~12,000 lines)

**Filtered out:**
- 3 non-game sections (~85 lines total)
- See `filtered_sections` in YAML for details

**Extracted:**
- Major events: 5
- New NPCs: 1 (Farmer Wilkins)
- New locations: 2 (The Beaver Dam, Old Mill)
- New items: 1 (Coyote Fang Necklace)
- Entity updates: 3 (Castor, Sir Roderic, Garland)
- Questions raised: 4
- Questions resolved: 1
- Arc progress: 2 arcs updated
- Notable quotes: 3
- Rules clarifications: 2

**Unresolved references (for review):**
- "the old wizard" (~line 1200) — Garland? Unknown NPC?
- "the Shepherd's Teeth" (~line 2400) — Witch Stones? New location?

**Output:** inbox/transcripts/extracted/session-01-extracted.yaml (1,847 tokens)

**Next step:** Review the YAML, then run incorporate-session
```

---

## Next Step

After extraction, review the YAML file:
- Check `filtered_sections` — anything important accidentally filtered?
- Check `unresolved_references` — can you clarify any?
- Check `new_entities` — correct categorization?

Then run the `incorporate-session` skill:

```
incorporate-session inbox/transcripts/extracted/session-01-extracted.yaml
```

That skill will:
1. Read the small YAML file
2. Create/update KB entity files
3. Generate the session summary file
4. Propose entity aliases
5. Move the original transcript to `processed/`

If you find something was incorrectly filtered, you can:
1. Check the prepared transcript at `inbox/transcripts/prepared/`
2. Manually add the missing information to the YAML
3. Re-run incorporate-session

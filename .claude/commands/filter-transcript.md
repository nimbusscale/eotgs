# Skill: Filter Transcript

**Purpose:** Mark non-game-related sections in a prepared transcript with HTML comments for human review.

**Input:** A prepared transcript file from `inbox/transcripts/prepared/`

**Output:** Same transcript with HTML comments marking non-game sections, saved to `inbox/transcripts/filtered/`

---

## Workflow

### Step 1 — Discover transcripts

List files in `inbox/transcripts/prepared/`.
Exclude `.gitkeep`.
If no prepared transcripts exist, report that and stop.

If the user specified a file as an argument (`$ARGUMENTS`), use that file.
Otherwise, process files one at a time, confirming with the user before each.

### Step 2 — Read the transcript

Load the full prepared transcript into context.
Note the total line count for the summary report.

The expected line format is:

```
[1/24/2026 1:07 PM] Speaker: Transcript text here...
```

### Step 3 — Scan for non-game sections

Read through the transcript and identify **contiguous blocks** of lines that are non-game chatter.
A "section" is one or more consecutive lines that are all non-game.

Classify each line using the rules in the Classification Rules section below.
Group consecutive non-game lines into sections.

### Step 4 — Mark non-game sections

Wrap each contiguous block of non-game lines with HTML comment markers:

```
<!-- NON-GAME SECTION: {brief reason} -->
[timestamp] Speaker: Non-game line...
[timestamp] Speaker: Another non-game line...
<!-- END NON-GAME SECTION -->
```

**Reason labels** — use the most fitting label for the block:

| Label | Use when |
|---|---|
| `break/afk` | AFK announcements, bathroom breaks, food/drink runs, waiting for someone to return |
| `technical issues` | Discord problems, audio issues, mic trouble, connection drops, notification settings |
| `scheduling` | Coordinating session times, availability, calendar planning |
| `real-world chatter` | Personal anecdotes, news, life updates unrelated to the game |
| `off-topic banter` | Jokes, banter, and side conversations with no game content |

If a block spans multiple categories, use the dominant one.

### Step 5 — Write output

Save the marked transcript to `inbox/transcripts/filtered/`.

**Filename rule:** Replace `-prepared` with `-filtered` in the original filename.

Example:
```
inbox/transcripts/prepared/session-2026-01-24-prepared.txt
→ inbox/transcripts/filtered/session-2026-01-24-filtered.txt
```

### Step 6 — Report summary

After processing, report:

```
## Filtered: {filename}

**Total lines:** {n}
**Non-game sections marked:** {n sections}
**Total lines marked:** {n lines} ({percentage}%)

**Sections:**
- Lines {start}-{end}: {reason}
- Lines {start}-{end}: {reason}
- ...
```

---

## Classification Rules

### NON-GAME — mark these

| Category | Examples |
|---|---|
| Real-world chit-chat | Personal anecdotes unrelated to the game, "how's work going", weekend plans |
| AFK / breaks | "I'm going to get some water", "brb", waiting chatter while someone is away |
| Technical issues | Discord problems, audio issues, mic trouble, notification settings, recording setup |
| Scheduling | "When's the next session?", coordinating availability, calendar discussion |

### GAME-RELATED — do NOT mark

| Category | Examples |
|---|---|
| In-character dialogue and narration | Characters speaking, GM describing scenes |
| Rules discussions | "How does grappling work?", ability clarifications, looking up rules |
| Character ability discussions | "My character can do X", class features, spell effects |
| World-building discussion | Lore, history, geography, factions, culture |
| Dice roll announcements | "I rolled a 14", "That's a hit", roll results |
| Session planning (in-game) | "So should we go to the dungeon or the town?", tactical planning |
| Game-referencing banter | Jokes and banter that reference game content, characters, or events |

---

## Edge Cases

**Mixed blocks:**
If a non-game section has a single game-related line sandwiched between non-game lines, include it in the marked block — the human reviewer will sort it out.
But if game content resumes for 2+ consecutive lines, end the non-game block before them.

**Session start chatter:**
Sessions often begin with greetings, tech setup, and small talk before game content starts.
Mark pre-game chatter as `technical issues` or `real-world chatter` as appropriate.

**Uncertainty — err toward keeping:**
When uncertain whether a line is game-related or not, do NOT mark it.
It is better to leave non-game content unmarked than to accidentally mark game content.
The human reviewer can always mark additional sections.

**Short interjections:**
A single "lol" or "haha" between game lines is NOT a non-game section — leave it unmarked.
Only mark blocks where the conversation has genuinely shifted away from game content.

**GM announcements about recording/setup:**
Lines about recording, transcription tools, or session logistics at the start are `technical issues`.

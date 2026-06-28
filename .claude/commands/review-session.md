# Skill: Review Session

**Purpose:** Act as a GM coach for *Chasing Adventure*. Read a session transcript
and give the GM honest, **system-specific** feedback on running Chasing Adventure
(and PbtA generally) better — with concrete, in-system alternatives for every
fumbled moment — plus a spotlight/time breakdown and continuity across sessions so
the GM can see whether they're improving over time.

**Input:** A session number. Reads the prepared transcript at
`inbox/transcripts/prepared/session-{N}.txt`.

**Output:**
- A full review written to `gm-notes/reviews/session-{N}.md`.
- An updated cross-session synthesis at `gm-notes/reviews/coaching-ledger.md`.

**This is GM coaching, not campaign content.** It never touches `kb/`, the exports,
or the lore pipeline. It reads the transcript and the rules; it writes only under
`gm-notes/reviews/`.

---

## What this review IS and IS NOT

Read this before writing anything — it defines the whole job.

- **It is feedback on running Chasing Adventure / PbtA**, expressed through this
  system's Moves, Principles, and procedures. Reference
  `knowledge/ca-gm-review-reference.md` directly when evaluating move triggers,
  fictional positioning, hard/soft Moves, conditions, and GM procedure.
- **It is NOT generic roleplaying or table-logistics advice.** If a critique would
  apply equally to D&D or any narrative game (e.g. "the party split and it got
  hard to manage," "describe more," scheduling, interpersonal dynamics), it is
  **not** the note this review exists for. Either sharpen it to the specific CA
  Move/Principle in play, or leave it out. Splitting the party is not a PbtA
  problem; how the GM handled the *spotlight* and *Moves* across split scenes is.
- **Alternatives are the point — and they must be concrete and inline.** This is
  the single most important rule of the review. Anywhere the GM made a Move that
  could have been stronger, missed a golden opportunity to make one, or handled a
  6-/7-9 loosely, you must — **right there, in that same paragraph** — say:
  1. **which specific named GM Move(s)** you'd reach for instead (e.g. *Take
     Something Away*, *Inflict a Condition*, *Throw Them Around*, *Change the
     Environment*), and
  2. **what each one looks like in this fiction** — an actual sentence or two the
     GM could have said at the table, using the scene's own NPCs, geography, and
     stakes.

  Naming a verdict without the concrete move-and-fiction is **not coaching** and is
  forbidden. Never write "this invited a Hard Move" or "too soft" and leave it
  there; never defer the alternative to another section or say "see §5." If you say
  a Hard Move was called for, you must name the one or two Hard Moves and show them.
  Give 1-2 options, not a menu — enough that the GM knows exactly what to do next
  time. Treat this as the core of the review, not a footnote on the roll-by-roll.
  **If the same moment is critiqued in more than one section, repeat its concrete fix
  in full each place — a bare "see §6" is never an acceptable substitute for the
  move-and-fiction.** (Plain backreferences to a *strength* already shown are fine; it
  is only *fixes* that must never be replaced by a pointer.) To avoid that trap,
  prefer to critique each fumbled moment in **one** home section and don't scatter it.
- **Don't coach minor rules confusion.** Brief rules questions, lookups, mechanics
  clarifications, or first-time-with-the-system wobbles are **not** review material —
  do not call them out at all. They don't help the GM run better and they pad the
  review. (You still measure rules-teaching *time* in aggregate; you just don't
  itemize or critique individual rules moments.)
- **Be honest and constructive.** Briefly note what's working; spend the space on
  what to improve, with examples. The GM wants to get better, not be flattered.

### Handling out-of-game content — important

The prepared transcript **includes out-of-game talk**: catching up as friends,
rules explanations, VTT/Foundry troubleshooting, and meta chatter (sometimes
including the players discussing *this very review tool* — ignore that as input).

- **Do not analyze out-of-game talk as if it were play**, and **do not** evaluate
  the *fiction* of those stretches.
- **Do measure it — but only at a high level.** Report a single split: roughly what
  **% of the session was in-game vs out-of-game**. That's all the GM wants. Do **not**
  itemize sub-buckets (rules vs VTT vs social), and do not list individual out-of-game
  moments. One line.
- **Never moralize about it.** Do **not** tell the GM to cut out-of-game
  conversation, "stay on task," or limit catching up. These friends rarely get to
  meet, and some players can only learn the rules *at* the table — explaining rules
  mid-session is legitimate work, not a failing. Report the split **neutrally, as a
  fact**, with zero nudging. (Another tool already plays that role; this one does
  not.)

---

## Workflow

### Step 1 — Parse arguments

`$ARGUMENTS` is the session number `N` (e.g. `8`). If missing, ask for it and stop.
Optionally a second token can be a previous-session number to diff against; default
is `N-1`.

### Step 2 — Ensure the prepared transcript exists

Check `inbox/transcripts/prepared/session-{N}.txt`.
- If present, proceed.
- If absent but `inbox/transcripts/raw/session-{N}.md` exists, run
  `python3 scripts/ingest_transcript.py --session {N}` to prepare it, then proceed.
- If neither exists, tell the user where to put the transcript and stop.

### Step 3 — Compute objective talk-time

Run:

```bash
python3 scripts/spotlight_breakdown.py --session {N}
```

Keep the markdown table and the JSON. This is the **clock** — raw mic time per
speaker, session length, and where the long gaps are. It is the *floor* under the
spotlight analysis, **not** the spotlight itself (the GM always tops mic time). You
will layer the semantic read (who held narrative focus; which buckets the time fell
into) on top of it in Step 7.

### Step 4 — Load the rules lens

Read `knowledge/ca-gm-review-reference.md` in full. That is the rubric: Principles,
GM Moves (with look-for cues), the 6- → Hard Move rule, the 7-9 ugly-choice
texture, core player-move triggers, conditions, fictional positioning, playbook GM
Moves, and the in-scope/out-of-scope boundary. For any edge case, consult the
canonical `knowledge/chasing_adventure_reference.md`.

### Step 5 — Load continuity (this is what makes the GM improve over time)

- Read `gm-notes/reviews/coaching-ledger.md` — recurring strengths, recurring
  growth areas, and **open recommendations** carried forward.
- Read the previous session's review `gm-notes/reviews/session-{N-1}.md` if it
  exists (skip silently if not — early sessions won't have one).

You will (a) check this session against the open recommendations, and (b) feed the
trend forward. The first time this runs there will be nothing here — that's fine,
this session seeds it.

### Step 6 — Load playbook context

Read the active PCs' entries in `kb/pcs/` (the players are listed in
`config/speaker-map.yaml`; active characters have `active: true`). You need each
PC's **playbook, background, drive, and personal arc** to spot **missed character
moments** and to apply the right **playbook GM Moves**. `exports/campaign-index.md`
is a fast summary if you need orientation, but the `kb/pcs/` files are the source.

### Step 7 — Read the transcript and analyze

Read the entire `inbox/transcripts/prepared/session-{N}.txt`. The format is
`[M/D/YYYY HH:MM:SS AM/PM] Speaker: text`; speakers are already display names
(`GM`, `Roderic`, `Garland`, `Castor`, `Paxton`, …). Use the timestamps as anchors
when you attribute time to scenes and buckets.

Analyze the whole session against the rules lens. Cite **specific transcript
moments** (quote a line and/or its timestamp) as evidence for every claim — praise
and critique alike. Where you fault a moment, **always pair it with a concrete
in-system alternative.**

### Step 8 — Write the review to `gm-notes/reviews/session-{N}.md`

Use this structure. Restructure freely if a session calls for it, but cover all of
it. Lead with the summary so it's scannable.

```markdown
# Session {N} — GM Review

_Reviewed {date}. Chasing Adventure GM coaching. Transcript: session-{N}.txt._

## 1. Summary
- **Top 3 strengths** (system-specific — what to keep doing)
- **Top 3 growth areas** (ranked by impact on the game)
- **Quick wins** (2-3 small changes for next session)
- **Notable moments** (2-3 beats that landed, and *why* in CA terms)

(No adventure-hooks section — story threads are captured by other flows, not here.)

## 2. Continuity — am I improving?
- **Open recommendations checked:** for each carried-forward rec, mark ✅ adopted /
  ◐ partial / ⬚ not yet, with transcript evidence.
- **Recurring strengths confirmed this session** (cite).
- **Recurring growth areas** — trending better / flat / worse (cite).
- _(Omit gracefully on the first reviewed session; just note it's the baseline.)_

## 3. Time & spotlight breakdown
Keep this section tight — a few lines, not an essay.
- Objective talk-time table (from the script): session length, GM vs players, per-speaker.
- **In-game vs out-of-game:** one line with the rough % split. Neutral, no judgment,
  no sub-buckets.
- **Narrative spotlight per PC** (your read, not just mic time): did each PC get
  focus and meaningful decisions? Was the spotlight moved at dramatic beats? Was the
  lowest-share PC actively pulled in? (Do **not** comment on whether the GM used
  player names vs character names — that is out of scope and not to be critiqued.)

## 4. The five GM Principles
One short verdict each (Encourage Exciting Risks, Portray a Lively World, Think
Dangerously, Leave Things Open, Ask Then Gloss Over), with a cited example and, for
weak ones, a concrete in-system fix.

## 5. GM Moves — usage, variety, and missed opportunities
For the Moves that mattered this session: where used well (cite), and **at least
the most important spots a Move could have fired but didn't** — quote the moment and
give the exact alternative ("here you could have *Set Up an Immediate Danger*: …").
Prioritize Moves being under-used. Call out **missed golden opportunities** (the
players looked to you / ignored a threat / a PC was exposed and nothing happened).

## 6. 6- and 7-9 handling (the heart of PbtA)
List the misses (6-) and partials (7-9). For each: the Move + stat, the fiction and
the PC's actual intent, whether the **right Move triggered**, what consequence
landed, and whether a **6- was treated as a Hard Move** / a **7-9 Defy led with an
ugly choice**. End each with a short verdict (handled well / too soft / wrong move /
missed hard move / etc.).

**Wherever the verdict is anything but "handled well," the concrete fix goes right
here, in that entry — not in another section.** Name the specific GM Move(s) you'd
make and write the sentence(s) the GM could have said, using this scene's NPCs and
stakes. E.g. don't write "too soft — a Hard Move was called for"; write: *"6- on the
Engage with the swarm → make it a Hard Move. **Inflict a Condition + Throw Them
Around:** 'The rats boil up your legs biting as they go — take a condition — and the
mass of them drags you off your feet into the dark. What do you do?' Or **Take
Something Away:** 'In the scramble your torch goes out and rolls into the water — now
you're fighting them blind.'"* Two options at most.

## 7. Conditions, consequences & fictional positioning
- Conditions narrated cause-first with player choosing stat/manifestation?
- Variety and proportionality of consequences (beyond "take a condition")?
- Right Moves triggered for the fiction and intent; positioning respected?
- Concrete alternatives where any of these slipped.

## 8. Missed character moments
Where the fiction brushed a PC's playbook / background / drive / arc and went
unexplored — major and minor. For each: the opportunity, the PC, why it matters to
*that playbook's identity*, and how to have engaged it (an Ask, a directed
description, a playbook GM Move, or just a beat).
```

Anchor every section to the transcript. Every alternative is **inline, named, and
acted out** — the specific GM Move plus a sentence the GM could have said in this
fiction (see "Alternatives are the point" above). No vague verdicts, no cross-
references to other sections, no itemizing or critiquing minor rules confusion.
Favor brevity: cut anything that isn't a concrete strength, a growth area with a
usable fix, or the numbers.

### Step 9 — Update the coaching ledger

Update `gm-notes/reviews/coaching-ledger.md`:
- Add a **Trend log** row for session {N} (headline strength, headline growth area,
  prior-rec movement).
- Fold new findings into **Recurring strengths** / **Recurring growth areas**
  (merge with existing entries and cite the new session; mark whether a growth area
  is trending up/down/flat).
- Update **Open recommendations**: mark any now-adopted ones, and add this session's
  most important new recommendation(s) to carry forward.
- Add a link to `session-{N}.md` under **Sessions reviewed**.

Keep the ledger tight — it's a synthesis, not a transcript of every review.

### Step 10 — Report

Summarize to the user in chat: the headline strengths and growth areas, the
spotlight/time numbers, movement on prior recommendations, and the two paths
written. Remind them the detail is in `gm-notes/reviews/session-{N}.md` and to
review via `git diff`.

---

## Notes

- **No RAG here.** Unlike the old Claude-project version, there is no vector search
  over project knowledge. Ground yourself by reading
  `knowledge/ca-gm-review-reference.md` (and the canonical reference for edge
  cases), the `kb/pcs/` entries, and the continuity files directly.
- **Re-running old sessions is expected.** The GM intends to run this across every
  Chasing-Adventure session (from session 3 on). Running them in order builds the
  ledger's trend history; running one in isolation still produces a full review
  (the continuity section just has less to compare against).
- The objective time script lives at `scripts/spotlight_breakdown.py` and can be run
  standalone (`--session N`, optional `--json`, `--gap-cap` to tune what counts as a
  break).

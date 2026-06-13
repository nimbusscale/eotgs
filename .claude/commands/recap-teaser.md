# Skill: Recap-Teaser

**Purpose:** Generate a dramatic recap-teaser for the next session, written in pulp radio "next time on" style, to jog players' memories and build excitement.

**Output:** A new session file in `kb/sessions/` with the recap-teaser ready for the GM to read aloud.

---

## Workflow

### Step 1 — Determine next session number

Glob `kb/sessions/session-*.md` to find the highest session number N. The next session is N+1.

### Step 2 — Check for GM plans

Check if `inbox/next-session-plans.md` exists.
- If it exists, read it — this is GM context about what's planned for the upcoming session. Use it to inform the teaser's hooks and direction without spoiling specifics.
- If it does not exist, ask the user: "Do you have any plans or context for session {N+1} you'd like me to incorporate? (Type your notes, or 'no' to proceed without them.)"

### Step 3 — Read source material

Read the following files for campaign context:
- `exports/campaign-index.md` — current campaign state, PC summaries, active story arcs
- `exports/sessions.md` — session summaries, major events, and existing recap-teasers

Do NOT read individual session files — the exports contain everything needed.

### Step 4 — Generate the recap-teaser

Write 2-3 paragraphs in the following style:

**Voice & Tone:**
- Dramatic present tense, pulp radio narrator style — "next time on" energy
- Short, punchy sentences. One sentence per line.
- Address PCs by name — reference what they did, what they face, what's at stake for them personally
- End with a hook or cliffhanger that makes players eager to pick up the story
- No game mechanics, no meta references (never say "the session", "the GM", "the players", "dice")
- High-level memory jog of where things left off + excitement for what's coming

**Format:**
- Italic paragraphs (wrap each paragraph in `*...*`) — do NOT use blockquote `>` syntax
- Use **bold** on key names, places, items, and concepts as memory anchors for skimming (e.g., **Aurelion**, **Second Harvest**, **the Laughing One**)
- Separate paragraphs with a blank line

**Quotes:**
- Optionally weave in 1-2 notable quotes from the most recent session as dramatic callbacks — only if they fit naturally. Never force a quote in.

**Length:**
- 2-3 paragraphs. Match the length and density of the session 3 and 4 teasers (session 2 is longer than typical, session 1 is not representative).

**GM Plans:**
- If GM plans were provided, let them subtly shape the teaser's hooks and direction — hint at what's coming without giving away plot beats. The teaser should feel like it's building toward something specific without revealing it.

### Step 5 — Write the session file

Create `kb/sessions/session-{N+1}.md` with this structure:

```markdown
# Session {N+1}: [Evocative Title]

**Date Played:**

## Recap-Teaser

[italic+bold teaser paragraphs here]
```

The title should be evocative and thematic, matching the style of existing titles (e.g., "Heralds of Ruin", "Beneath the Golden City", "The Sleeping God").

Leave **Date Played:** blank — it will be filled in after the session.

### Step 6 — Clean up GM plans

If `inbox/next-session-plans.md` was read in Step 2, move it to `inbox/next-session-plans-used.md`:

```bash
mv inbox/next-session-plans.md inbox/next-session-plans-used.md
```

### Step 7 — Print the teaser

Print the full recap-teaser text so the GM can review it before committing.

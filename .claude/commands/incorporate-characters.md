# Skill: Incorporate Characters

**Purpose:** Fold Foundry character-sheet snapshots from `inbox/characters/` into the
existing PC entries in `kb/pcs/`, reconciling the live mechanical build (stats, playbook,
moves, equipment) into each entry's own sections — **in place, by judgment**, not as a
separate block.

Players edit their sheets in the live Foundry "Echoes of the Godstorm" world
(`pbta-test`, Chasing Adventure on the `pbta` system) between games. `scripts/pull_actors.sh`
pulls those sheets and writes one snapshot per PC to `inbox/characters/<slug>.md`. This
command merges each snapshot into `kb/pcs/<slug>.md`.

**Writing convention:** All narrative prose in KB files uses **one sentence per line**
(semantic linebreaks). Move/ability lists and stat lines are not prose — keep them as the
existing entry formats them (bulleted `**Move** — description` lists, the `STR X, DEX X …`
stat line, etc.).

**Core principle — update, don't duplicate.** The snapshot is the source of truth for the
*mechanical build*. The entry already describes that build in prose (Concept, `## Stats`,
`## Playbook`, `## Key Traits & Abilities`, etc.). Your job is to make those existing
sections agree with the snapshot — rewriting them in place — **never** to append a parallel
"Character Sheet" section that repeats stats or moves.

---

## Workflow

Process each snapshot file individually.

### Step 1 — Discover snapshots

List files in `inbox/characters/` (exclude `processed/` and `.gitkeep`).
If none exist, report that and stop — the user likely needs to run `bash scripts/pull_actors.sh` first.
Process snapshots **one at a time** in alphabetical order.

### Step 2 — Load context (context-efficient)

| What to read | How |
|---|---|
| The snapshot file `inbox/characters/<slug>.md` | Read in full |
| The target entry `kb/pcs/<slug>.md` (the `pc_slug` in the snapshot frontmatter) | Read in full |
| `config/entity-aliases.yaml` | Read in full (small) — for `[[wiki-link]]` resolution |
| `review/pending-changes.md` | Read in full (small) |

If `kb/pcs/<slug>.md` does not exist, flag it in `review/pending-changes.md` and skip
(this command updates existing PCs; it does not create entries).

### Step 3 — Reconcile the build into the entry's sections

Compare the snapshot against the entry and update the entry so it reflects the live sheet.
Work section by section:

- **Stats** (`## Stats` line, e.g. `STR 0, DEX 1, INT 1, WIS 2, CHA -1`): overwrite with the
  snapshot's stat values. There must be exactly one stats line in the entry.
- **Playbook / Level** (`## Playbook`): update the playbook name and level to match.
- **Moves / abilities** (`## Key Traits & Abilities`, or the entry's equivalent moves list):
  this is the heart of the merge.
  - **Add** moves present on the sheet but missing from the entry, in the entry's existing
    style (e.g. `- **Move Name** — short description`). Summarize the snapshot's rules text
    into one tight line in the entry's voice; do not paste the full Foundry rules text.
  - **Reconcile names.** The entry may describe an ability under a colloquial or wrong name.
    Match by *effect*, not just by label, and rename to the sheet's canonical move name.
    (Example: a between-worlds / dissolve-into-wind power described loosely under
    "At One With The World" is actually the **Bridge Between Worlds** move — attach the
    description to the correct move and keep "At One With The World" as its own base move.)
  - **Remove or correct** entry moves that are not on the sheet only when you're confident
    they're stale mechanics (not narrative flavor). If unsure, keep and flag (Step 4).
  - Preserve the entry's hand-written flavor notes (e.g. "Shapeshifting Notes") — those are
    narrative, not sheet data. Do not delete them.
- **Equipment / assets**: fold notable gear (signature weapons, distinctive items) into the
  entry where it already tracks assets. Skip generic adventuring sundries unless the entry
  already lists them.
- **Cross-class picks**: a Fighter carrying Wizard moves, etc., is normal — represent them
  the way the entry already does (e.g. a "Cross-Class … Moves" subsection).
- Leave **Drive** and **Background** prose as authored unless the snapshot clearly adds or
  changes a mechanical detail; prefer the entry's narrative wording.

Preserve all existing `[[wiki-links]]` and add new ones where a move/asset references a known
entity (resolve via `config/entity-aliases.yaml`). Do not invent links.

Do **not** touch narrative sections the sheet says nothing about: Concept, Relationships,
Favors, Hooks, Religion, Current Threads, Session Appearances.

### Step 4 — Flag conflicts (do not silently resolve)

Add entries to `review/pending-changes.md` for anything you cannot confidently reconcile:

```markdown
## Contradictions
- inbox/characters/castor.md: sheet shows Level 3 but pcs/castor.md narrative implies he never advanced — confirm.
- inbox/characters/sir-roderic-lightbearer.md: entry lists "Eyes of the Faithful" as Advanced; sheet has it as a base class move — which is canon?
```

Also flag: a move on the sheet whose effect you cannot map to anything in the entry and
aren't sure how to phrase; an entry move absent from the sheet that might be either stale or
deliberate flavor; a stray/blank sheet move (e.g. an item literally named "Move", or an empty
"Equipment from Background" placeholder) — note it for cleanup in Foundry rather than copying
it in.

### Step 5 — Move the processed snapshot

After updating the entry, move the snapshot:

```
inbox/characters/<slug>.md → inbox/characters/processed/{YYYY-MM-DD}/<slug>.md
```

Use today's date (date of processing). Create the date subdirectory if needed.

### Step 6 — Report summary

Per character:

```
## Incorporated: castor

**Entry updated:** kb/pcs/castor.md
- Stats refreshed (WIS 2 → matches sheet)
- Playbook set to Druid, Level 3
- Added moves: Resist Instinct, Bridge Between Worlds
- Renamed: "between-worlds power" prose → attached to Bridge Between Worlds (Advanced)

**Flagged for review:**
- (none) | or list pending-changes entries

**Snapshot moved:** inbox/characters/processed/{date}/castor.md
```

---

## Edge Cases

- **No matching entry:** flag in `pending-changes.md`, skip; do not create the PC here.
- **Entry already matches the sheet:** report "no changes" and still move the snapshot.
- **NPC actors** (e.g. Mira, who lives in `kb/npcs/`): only handled if the actor map points
  to an npcs slug; otherwise the snapshot won't exist. Out of scope by default.
- **Idempotency:** re-running after a fresh pull with no Foundry changes should produce no
  entry edits — the sections already agree.
- **Never** add a `## Character Sheet` (or similar) block that duplicates stats/moves already
  present elsewhere in the entry. If you find one from an earlier approach, collapse it into
  the proper sections and delete the block.

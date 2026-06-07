# Skill: Illustrate Session

**Purpose:** Turn one session of the campaign into a small set (3–5) of validated
campaign illustrations — one per key moment — and register them in a session
`Gallery`. This is the batch orchestrator on top of the single-picture
`illustrate-scene` skill: it picks the moments, lets the human approve the scene
**descriptions before any image is generated**, fans out one generation
subagent per approved scene, then promotes the approved images.

**Invocation:** `/illustrate-session [N]` — optional session number; default is
the latest session.

**Architecture (read `dev/illustrate-architecture.md`):** This command is a
**thin orchestrator that runs in the main context and never reads a candidate
image itself.** Every image read, candidate, and refine pass is trapped inside a
per-scene subagent that follows the `illustrate-scene` skill end-to-end and
returns only `{ image_path, verdict, notes }`. That isolation is the whole point
— it is what keeps the main context from filling with a dozen throwaway images.
Use exactly **one level** of subagent nesting (this command → per-scene
subagent); the subagent runs `illustrate-scene` inline, it does not nest further.

There are **two human gates** and you must stop at each:
- **GATE 1 (after Step 3):** approve/edit the scene **descriptions**. No image
  generation and **no API spend** happens before this gate clears.
- **GATE 2 (after Step 4):** approve/regen/drop the generated candidates.

---

## Workflow

### Step 0 — Resolve the session

If the user passed a number `N`, use it. Otherwise find the latest session file:

```bash
find kb/sessions -name "session-*.md" | grep -v index | sort -V | tail -1
```

From the resolved path derive:
- `N` — the session number (e.g. `6`).
- the **arc subdir** — the directory segment under `kb/sessions/` (e.g.
  `forgotten-and-forsaken`). You need it for the Step 6 image-map key
  `sessions/<arc>/session-N`.

Read the session file at that path.

### Step 1 — Pick 3–5 key moments

Mine the session for the most visual, distinct beats. **Read the `## Summary`
and `## Major Events` together** — the Summary carries the richer visual detail
and the Major Events confirm the durable facts; also skim `## Notable Quotes`
for emotional anchors. Favor **variety** across the session's threads and
characters (don't draw five versions of the same beat).

For each chosen moment, draft a brief matching the `illustrate-scene` contract:

- `name` — `session-N-<short-kebab>` (e.g. `session-6-paxton-burns-barge`). This
  is the output slug.
- `description` — **required.** What is happening, who is doing what, the mood.
- `characters` — names present (may be empty for an establishing shot).
- `location` — place name (or a free description if it has no KB entity).
- `aspect_ratio` — default `16:9 landscape`.
- `weapons` — `hidden` for parley/quiet/ceremony moments, `shown` for combat.
- optional `mood` / `lighting` tweak.
- `caption` — one short narrative line (used as the gallery caption in Step 6).

**Ground every detail in the session text. Invent nothing that was not
narrated.** This is the hard rule. (The validating lesson — `session-6-paxton-
burns-barge`: the Summary says the creatures dragged at him *from the marsh* and
he found Senna *inside* the barge healing them; it does **not** put a horde of
tentacle-monsters on the shore. Draw the barge and the two figures the text
names, not a monster the text never placed there.)

### Step 2 — Pre-flight references (cheap; no image reads, no minting)

For each brief, resolve every character/location to a slug via
`config/entity-aliases.yaml`, then gather **every** image of that slug in
`config/image-map.yaml` — both its own entry (key **ends with** `/slug`) **and**
any guest image elsewhere whose `subjects:` list names the slug (see
`illustrate-scene` Step 2). Apply the **library-first reference priority** from
`illustrate-scene` Step 3:

- **PCs** → the `library` plate (always exists for Castor/Garland/Paxton/Roderic).
- **NPCs** → `library` plate → else `hero` → else the NPC's own `gallery` →
  else a **guest image** (an item under another entry — often a prior session
  gallery — whose `subjects` include this slug).

This is a cheap lookup — **do not read the images and do not generate
anything.** An entity is **ref-light only when it has no image anywhere** (no
own entry *and* no guest appearance) — flag those; that scene will be drawn from
its description plus whatever other references exist. An NPC who appeared in an
earlier session's gallery is **not** ref-light: note that you'll use that guest
image as their reference. Do **not** mint a reference plate here — plate minting
is a separate, human-initiated step (`generate-reference-plate`); just report the
gap.

### Step 3 — GATE 1: approve the scene descriptions

Present the set to the user. For each scene show its **`description`** (that is
where the detail lives and what they are approving), plus `characters`,
`location`, `weapons`, `aspect_ratio`, and any **ref-light** note. Invite them to
**approve / edit / swap / drop / add** scenes. Iterate conversationally until
they approve the set.

**No image is generated in this step. No API spend happens before GATE 1
clears.** Stop here and wait for the human.

### Step 4 — Generate (the isolation boundary)

Once the descriptions are approved, generation needs `OPENAI_ACCESS_KEY`. If it
is not set, ask the user to set it in this session first:

```
! export OPENAI_ACCESS_KEY=sk-...
```

Then spawn **one subagent per approved scene** (the Agent tool — one nesting
level only). Spawn them **in parallel** (multiple Agent calls in a single
message). Give each subagent:
- the approved brief for its scene, and
- an instruction to **follow the `.claude/commands/illustrate-scene.md` skill
  end-to-end** (resolve → select references by the library-first priority →
  write the scene-request → compose/generate → evaluate → bounded refine), and
- an instruction to return **only** the result object
  `{ image_path, verdict, notes }` and nothing else (no image dumps).

A ref-light entity is generated from its description plus the available
references. Each subagent's candidate lands in `image-test/<name>.jpg` (refines
→ `-vN`), with composed-prompt scratch in `image-test/.composed/`.

### Step 5 — GATE 2: review the candidates

Collect the `{ image_path, verdict, notes }` from every subagent and present the
set: each scene's `image-test/<name>.jpg` path + its verdict + notes. The user:
- **approves** a candidate,
- **requests a regen** — re-spawn just that one scene's subagent with the user's
  correction folded into the brief, or
- **drops** it.

Iterate until the user has settled which candidates to keep. Stop and wait at
this gate.

### Step 6 — Promote + register

For each **approved** candidate:

1. `mkdir -p images/sessions` (once).
2. **Copy** (do not move) the candidate to
   `images/sessions/session-N-<slug>.jpg`. Leave the candidate and its
   `.composed/` scratch in `image-test/`.

   ```bash
   mkdir -p images/sessions
   cp image-test/<name>.jpg images/sessions/session-N-<slug>.jpg
   ```

3. Register it in `config/image-map.yaml` under the key
   `sessions/<arc>/session-N` (the arc subdir from Step 0). Ensure that key has a
   `gallery:` list, and **append** one block-style item per approved image, with
   a `subjects:` list so the image is discoverable as a reference later:

   ```yaml
   sessions/forgotten-and-forsaken/session-6:
     gallery:
       - file: sessions/session-6-paxton-burns-barge.jpg
         caption: "Paxton burns Senna's barge and throws himself into the river"
         subjects: [paxton-lumnus, senna, havens-reach]
         description: "...note prominence/fidelity, e.g. 'only existing depiction of Senna (low detail)'."
   ```

   The `file` is the path **under `images/`** (block style, no inline `{}`). Use
   the one-line narrative `caption` from the brief.

   **`subjects:` is required and load-bearing.** List the canonical slug (the
   same one from `entity-aliases.yaml`) of every character AND the location
   **actually depicted with a usable likeness** in the image — this is what lets
   a future scene find this picture when an NPC has no entry of their own (the
   whole point of the cross-map lookup in Step 2). Omit a character who is in the
   beat but not usably depicted (e.g. shown only as a swirl of wind, or an
   off-screen name). Add a short `description` noting prominence/fidelity for any
   guest subject (e.g. "only existing depiction of Voss", "Senna glimpsed, low
   detail") so reference selection can weigh it. This step is the only place
   these new NPCs/locations get recorded, so getting `subjects` right here is
   what makes the next session's renders of them consistent.

After registering, tell the user the images will render in a `## Gallery` on the
session page at the next `/export-kb`. **This command does not build or deploy** —
it stops at registration.

---

## Guardrails

- **Never read a candidate image in the main context.** That churn belongs in the
  per-scene subagents; the whole point of the orchestrator is to stay light.
- **No generation before GATE 1.** Descriptions are approved first, on purpose —
  generation is the expensive step.
- **One nesting level.** This command spawns the scene subagents; those run
  `illustrate-scene` inline and never spawn their own.
- **Ground everything in the session text.** Don't add figures, monsters, or
  settings the Summary/Major Events didn't narrate.
- **`library` plates are reference-only.** They are committed under `config/` and
  are never published; only the promoted `images/sessions/*.jpg` are.

## Background reading

- `.claude/commands/illustrate-scene.md` — the single-picture worker each scene
  subagent runs (the brief contract, reference selection, compose/evaluate/refine
  loop). The orchestrator's briefs must match its input contract.
- `dev/illustrate-architecture.md` — the skill/subagent/script decomposition and
  the subagent-boundary rule this command embodies.
- `.claude/commands/references/evaluate.md` — the evaluation guide the scene
  subagent uses to decide accept/refine/flag.

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

The session frontmatter **may** carry two source-only keys you'll use in Step 1:
- `transcript:` — path to the prepared transcript (stable line numbers).
- `scene_sources:` — a labelled list of `{ beat, lines }` entries pointing into that
  transcript. These let you recover the concrete narrated detail behind each beat.
  Older sessions won't have them — that's fine; Step 1 degrades gracefully.

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
- `weapons` — `hidden` or `shown`, **derived from the span** (rule (b) below), not
  defaulted: `hidden` for parley/quiet/ceremony *and* for brawls the text narrates
  as bare-handed; `shown` only when drawn weapons are narrated.
- optional `negatives` — a list of "not in this scene" constraints, especially
  span-derived ones: invented weapons/props the text never named, and intent
  negatives (rules (b)/(c) below). Passed through to the scene-request `negatives`.
- optional `mood` / `lighting` tweak.
- `caption` — one short narrative line (used as the gallery caption in Step 6).
- optional `transcript_ref` — `{ file, lines }` recording the transcript span you
  grounded this beat in (see below). Pass it through to the generation subagent in
  Step 4 so it can pull extra detail during compose/refine. Omit when no
  `scene_sources` entry matched.

**Ground every detail in the session text. Invent nothing that was not
narrated.** This is the hard rule.

**Read the transcript behind each beat (when available).** The `## Summary` and
`## Major Events` are a compression of the transcript, so concrete scene detail
(positioning, appearances, blocking, lighting) the GM narrated is lost. If the
frontmatter carries `scene_sources`, then for each chosen beat:

1. Match it to the best `scene_sources` entry by its `beat` label (the beat that
   most closely names what your moment depicts).
2. **Read that entry's `lines` range from the `transcript` file** — use Read with
   `offset`/`limit` (e.g. `offset: <start>`, `limit: <end − start + 1>`). This is
   cheap text and consistent with the orchestrator's "stay light, no image reads"
   rule — you are reading the transcript, never an image.
3. **Ground the brief in what you find there** — the narrated staging the Summary
   dropped — while still obeying the "invent nothing not narrated" rule. Set
   `transcript_ref` to `{ file: <transcript path>, lines: <range> }`. As you read
   the span, apply the four grounding rules below.

**Grounding rules (apply to every transcript-backed beat).** Reading the span is
not enough — *how* you turn it into a brief is what separates an accurate-but-flat
image from a good one. These four were learned from failures, each tied to a real
miss:

- **(a) Two layers: foreground staging + background atmosphere.** Write the
  `description` in two layers. The **foreground** is the literal action/staging
  from the span. The **background** is the scene's *atmosphere* — the setting, the
  light, the wider world visible behind the action. The Summary and the climax
  lines drop atmosphere; recover it from the span's **establishing lines** (the
  setup the GM narrated before the payoff — the `lines` range already includes
  them if extraction did its job) **and** from the entity's **own KB page** (read
  the `location`/world entry for how the place looks). Do not let the foreground
  action crowd the backdrop out of the prompt — name the backdrop explicitly as
  its own clause, or the model renders only the foreground. *(The realm-of-the-
  forgotten beat failed exactly here: the brief was all Garland/child foreground
  and dropped the distant lost city + drifting forgotten people the span actually
  described — so the image was accurate but lifeless next to a looser one that
  free-associated the atmosphere.)*
- **(b) Derive `weapons` and "not-narrated" negatives from the span — don't
  default.** Read what the span actually says about armament and props. If the
  text has fighters bare-handed, grappling, or "coming to blows" with no named
  weapon, set `weapons: hidden` and add explicit negatives against invented arms
  (e.g. `"no spears, no knives — the warriors are bare-handed"`). Only set
  `weapons: shown` when the span names drawn weapons. The blunt default licenses
  the model to invent a wall of spears the table never described.
- **(c) State intent and emotion explicitly — the model composes literally.** A
  literal pose ("cradling the child out in front of him") can read as the
  *opposite* of what was meant ("offering it" vs. "shielding it from them"). The
  human infers the intent from context; the model does not. So spell out the
  emotional read and the body-language intent in the `description`, and add an
  intent **negative** (e.g. `"shielding the child, NOT offering it"`;
  `"grief-stricken, not calm or stoic"`). Make the emotional focus an explicit
  clause when the beat's power is emotional.
- **(d) Carry the span's negatives into the brief's `negatives` list** so the
  generation subagent and the evaluator both inherit them (see Step 4 and
  `references/evaluate.md`). A negative that lives only in your head can't be
  checked.

**Graceful fallback:** when the frontmatter has no `scene_sources`, or a chosen beat
has no good match (older sessions), draw the `description` from the `## Summary` /
`## Major Events` exactly as before and omit `transcript_ref`. Do not block on a
missing transcript. Rules (a)–(d) still apply as far as the Summary and the
entity KB pages allow — atmosphere and intent come from those instead of a span. (The validating lesson — `session-6-paxton-
burns-barge`: the Summary says the creatures dragged at him *from the marsh* and
he found Senna *inside* the barge healing them; it does **not** put a horde of
tentacle-monsters on the shore. Draw the barge and the two figures the text
names, not a monster the text never placed there.)

### Step 2 — Pre-flight references (cheap; no image reads, no minting)

For each brief, resolve every character/location to a slug via
`config/entity-aliases.yaml`, then gather **every** image of that slug: its own
entry in `config/image-map.yaml` (key **ends with** `/slug`) **plus** every guest
image whose `subjects:` list names the slug — which `config/subject-index.yaml`
(generated, slug → image files) gives you directly (see `illustrate-scene`
Step 2). Apply the **library-first reference priority** from
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
- the approved brief for its scene — **including its `transcript_ref`** if the beat
  has one (so the subagent can Read that span, cheap text, to pull extra narrated
  detail during compose/refine), **its `negatives`, and its intent/emotion clause**
  (rules (b)/(c)) so they survive into the scene-request, and
- an instruction to **follow the `.claude/commands/illustrate-scene.md` skill
  end-to-end** (resolve → select references by the library-first priority →
  write the scene-request → compose/generate → evaluate → bounded refine), and
- an instruction that **a refine pass must re-assert the scene's signature
  "tells"** — the one or two features that make a subject recognizable (Castor's
  oversized beaver buck teeth, Garland's elven ears, a character's heraldry). A
  worded correction aimed at one fix routinely drops a *different* signature
  feature; the correction must restate the tells to protect, not just name the
  defect. *(The gorilla refine that fixed the child's stone face silently lost the
  buck teeth — exactly this regression.)*
- an instruction to return **only** the result object
  `{ image_path, verdict, notes }` and nothing else (no image dumps).

(`transcript_ref` is additive and optional — `illustrate-scene`'s own contract is
unaffected; a brief without it behaves exactly as before.)

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

3. Register it in the **session file's frontmatter** —
   `kb/sessions/<arc>/session-N.md` (the arc subdir from Step 0) — under an
   `images:` block. Ensure that block has a `gallery:` list and **append** one
   item per approved image, with a `subjects:` list so the image is discoverable
   as a reference later:

   ```yaml
   # in kb/sessions/forgotten-and-forsaken/session-6.md frontmatter
   images:
     gallery:
       - file: sessions/session-6-paxton-burns-barge.jpg
         caption: "Paxton burns Senna's barge and throws himself into the river"
         subjects: [paxton-lumnus, senna, havens-reach]
         description: "...note prominence/fidelity, e.g. 'only existing depiction of Senna (low detail)'."
   ```

   The `file` is the path **under `images/`**. Use the one-line narrative
   `caption` from the brief. Do **not** hand-edit `config/image-map.yaml` — it is
   generated from this frontmatter.

   **`subjects:` is required and load-bearing.** List the canonical slug (the
   same one from `entity-aliases.yaml`) of every entity the image is a *usable
   reference for* — this is what lets a future scene find this picture (via
   `config/subject-index.yaml`) when an entity has no entry of its own (the whole
   point of the cross-map lookup in Step 2). The bar is "usable reference," not
   "present in the scene," and it differs by entity kind:
   - **Characters:** tag a character only if they are **depicted with a usable
     likeness** (face/build/outfit readable). Omit a character who is in the beat
     but not usably depicted (shown only as a swirl of wind, a back, or an
     off-screen name).
   - **Locations:** tag a location only if the image is a **usable establishing /
     representative view of that place** — not merely *where the scene is set*. A
     backdrop glimpse, an interior that says nothing about the place, or a setting
     named only in the caption does **not** count, even though the scene happens
     there. (This is why beaconhold/bonewall/havens-reach were pruned from
     session-6 — the scenes occurred there but showed no referenceable view; a
     location with no good view should stay honestly ref-light so it gets a real
     establishing plate later.) When in doubt, leave the location off.

   Add a short `description` noting prominence/fidelity for any guest subject
   (e.g. "only existing depiction of Voss", "Senna glimpsed, low detail") so
   reference selection can weigh it. This step is the only place these new
   NPCs/locations get recorded, so getting `subjects` right here is what makes the
   next session's renders of them consistent.

4. Run `python3 scripts/build_index.py` to regenerate `config/image-map.yaml`
   and `config/subject-index.yaml` from the updated frontmatter.

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

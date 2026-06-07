# Skill: Illustrate Scene

**Purpose:** Turn ONE image brief — a moment description plus the characters present and the location — into a single generated campaign illustration that matches the house style and keeps every character looking like themselves. This is the reusable single-picture engine. Use it whenever someone wants to illustrate, draw, render, or generate a picture of a campaign scene, moment, character, or place, even if they don't say "illustrate-scene." A future `illustrate-session` command (and other tools) will call this skill once per chosen moment.

**Input:** An image brief (see below). Provided by the user, by another command, or assembled by you from a session moment. ONE picture per invocation.

**Output:** A *validated* final image and a result object `{ image_path, verdict, notes }` — not just a raw first draft. The skill generates, reads the image back, evaluates it against the brief and the reference images, and refines (bounded) before returning the best result. The image lands at `image-test/<name>.jpg` (refine passes write `image-test/<name>-vN.jpg`), with the composed prompt at `image-test/.composed/<name>.json` (gitignored scratch). A generated scene is a *candidate*: the skill returns its path so a caller can collect it, but it does **not** publish. `images/` is reserved for publish-ready assets synced to the server; `image-test/` holds all scratch/test output. Neither is committed.

**Architecture:** This skill is the *judgment* layer; the deterministic work lives in two scripts. You resolve names to entities, pick the right reference images, and write a *scene-request* JSON. Then `scripts/compose_image_prompt.py` does the rest deterministically: it injects the house style around your references (the validated injection algorithm from `dev/house-style-injection.md`), assembles one JSON prompt document, and calls `scripts/generate_image.py` with the reference images. You never assemble the house style by hand — that is the composer's job. Your job is choosing *what* goes in.

---

## The image brief

The caller gives you some or all of:

- `description` — what is happening in the moment (required).
- `characters` — names of characters present (may be empty for a pure location/establishing shot).
- `location` — where it happens (a place name, or a free description if it has no KB entity).
- `aspect_ratio` — optional; default `16:9 landscape` for scenes. Use `2:3 portrait` for tall/vertical subjects, `square` for icon-like framing.
- `weapons` — optional; `shown` (default) or `hidden`. Use `hidden` for non-combat moments (planning, conversation, ceremony) so signature weapons and shields are kept out of frame.
- a lighting or mood tweak — optional; if given, put it in the scene block's `lighting`/`mood`.

If the brief is vague, fill the scene block with concrete, visual detail drawn from the campaign (see `exports/campaign-index.md` and the relevant KB pages). A richer scene block produces a better image; the composer passes it through verbatim and tells the model scene details take precedence over generic style defaults.

---

## Workflow

### Step 1 — Resolve each name to a slug

Read `config/entity-aliases.yaml`. Map each character name through its `characters:` section and each location through `locations:`. The value is the canonical slug (e.g. `Roderic → sir-roderic-lightbearer`, `Aurelion Tunnels → aurelion`). Names not in the alias map may still match a slug directly — slugify the name (lowercase, hyphens, drop articles/punctuation) and look for it in the next step.

### Step 2 — Find every image of each entity (own entry + guest appearances)

Read `config/image-map.yaml`. An entity's pictures live in **two** places, and you must gather both:

1. **Its own entry** — the entry whose key **ends with** `/slug` (e.g. slug `sir-roderic-lightbearer` → key `pcs/sir-roderic-lightbearer`; slug `aurelion` → key `locations/aurelion`). The key prefix (`pcs/`, `npcs/`, `locations/`, …) is the entity type and you do not need to know it in advance — match on the suffix.
2. **Guest appearances elsewhere** — any image item *anywhere in the map* (any entry's `hero`/`gallery`) whose `subjects:` list contains the slug. This is how you find pictures of an entity that does **not** own an entry — e.g. an NPC who only ever appears inside a session gallery (`sessions/<arc>/session-N`) or inside another character's gallery, or a page-less sub-entity (the `chryseum` images that live on `locations/aurelion`). This guest scan is **precomputed**: `config/subject-index.yaml` (generated) maps every slug → the list of image files that depict it, so you can look up your slug there directly instead of re-scanning every `subjects` list. (Both files are generated from kb frontmatter by `scripts/build_index.py`.)

So for each slug you end up with a candidate set = (its own entry's items, if any) + (every guest item whose `subjects` include it). Read each candidate's `description` to judge how usable it is (prominent vs. incidental, weapon-free vs. armed, which location view). Step 3 ranks them.

### Step 3 — Select the reference image per entity

Each entry has `hero`, `gallery`, and/or `library` items. Every item carries a `file`; library and most NPC/location items also carry a `prompt` (path to its spec JSON) and a `description`. Select by this priority:

- **For each character — apply the reference-selection priority:**
  - **PCs** (`pcs/…` keys: Castor, Garland, Paxton, Roderic) → **always the `library` plate** (its `file` + `prompt`). The PC `hero`/`gallery` is player-submitted in-world art with no prompt and must not be used as the identity reference. Castor has two plates — pick the **human** plate normally, the **beaver** plate when the moment shows him shapeshifted.
  - **NPCs** → walk the fallback in order: **`library` plate if one exists → else the `hero` image → else the NPC's own `gallery` → else a guest image (an item under some other entry whose `subjects` include this slug — e.g. a session gallery picture of them).** Take the `prompt` if the chosen item has one. Guest images rank last because they are lower-fidelity than a dedicated plate (smaller, partial, sometimes a single lit face in a busy scene) — but a guest likeness is far better than generating the character blind, and it keeps every later picture of an NPC consistent with the first. Use the candidate's `description` to judge: prefer a guest image that depicts the character prominently over one where they are incidental.
  - When `weapons: hidden`, prefer a weapon-free reference if the `description`s distinguish one.
- **For the location:** the specific view that fits the moment. Consider both the location's own entry (which often has several gallery views — read their `description`s and pick by the scene, e.g. for a scene inside the cathedral `aurelion` → the `chryseum-interior` item, not the approach shot) **and** guest images whose `subjects` include the location slug (a session scene set there can serve as an establishing reference when the location has no dedicated entry). Prefer a dedicated location view over an incidental backdrop.

**Path conventions:** a `library` item's `file` is **repo-root-relative** (e.g. `config/image/library/paxton-reference-plate.jpeg`); `hero`/`gallery` `file`s are under `images/` (e.g. `images/mira.jpg`). Use each path as written in the map.

**Image-only references are allowed.** A chosen item may have a `file` but no `prompt` (the NPC last-resort case). Use it anyway — emit it in the scene-request **without** a `prompt` field; the composer passes the image through as a likeness reference with no canon sub-prompt.

**Ref-light** means an entity has **no image at all** anywhere in the map — no own entry *and* no guest image whose `subjects` name it. Only then can you not reference it: note it to the user (it needs an image, ideally a plate) and generate the picture from the remaining references plus a rich, grounded scene block. (An entity that appears only as a guest subject is **not** ref-light — use that guest image as its reference.)

### Step 4 — Write the scene-request JSON

Write a scene request to a scratch path (e.g. `image-test/.composed/<name>-request.json` or `/tmp/<name>-request.json`). Schema:

```json
{
  "name": "roderic-confronts-voss",
  "type": "scene",
  "aspect_ratio": "16:9 landscape",
  "scene": {
    "description": "What is happening, who is doing what, the mood of the moment.",
    "composition": "Optional: framing, focal point, leading lines.",
    "lighting": "Optional: only if the moment needs specific light; otherwise omit and the house style supplies scene lighting.",
    "mood": "Optional.",
    "negatives": ["things to keep out, e.g. no spell glow, no monsters"]
  },
  "references": [
    { "role": "character", "name": "Roderic",
      "image": "config/image/library/roderic-reference-plate.jpeg",
      "prompt": "config/image/prompts/roderic-reference-plate-prompt.json" },
    { "role": "location", "name": "Aurelion Tunnels",
      "image": "images/aurelion-street-level.jpg",
      "prompt": "config/image/prompts/aurelion-street-level.json" }
  ],
  "weapons": "shown"
}
```

Notes:
- `name` is the output slug → `image-test/<name>.jpg`. Make it short, descriptive, kebab-case.
- `role` is `character` or `location`. The composer scopes palette by role: characters with a strong canonical palette (e.g. Roderic) stay bright even in a muted scene; the environment uses the muted world palette unless the location's own spec is a bright subject (e.g. the Chryseum interior). You don't manage any of that — just label roles correctly.
- `image`/`prompt` paths are repo-relative, taken verbatim from the map. PC plate `image`s sit under `config/image/library/…`; `hero`/`gallery` images sit under `images/…`.
- `prompt` is **optional** per reference. For an image-only reference (an NPC with a published image but no spec) omit the `prompt` field entirely — the composer accepts that and rides the image through as a likeness reference with no canon sub-prompt.
- Omit `scene.lighting` unless the moment genuinely needs its own light; an empty lighting lets the house style apply its scene lighting.

### Step 5 — Compose and generate

`generate_image.py` needs `OPENAI_ACCESS_KEY`. If it is not set, ask the user to set it in this session first, e.g.:

```
! export OPENAI_ACCESS_KEY=sk-...
```

Then run the composer (it writes the composed prompt and calls `generate_image.py`):

```bash
OPENAI_ACCESS_KEY=$OPENAI_ACCESS_KEY python3 scripts/compose_image_prompt.py --request image-test/.composed/<name>-request.json
```

This is the **first pass** and produces the base image `image-test/<name>.jpg`. To check the assembled prompt **before** spending on a generation (recommended when the brief is unusual), add `--dry-run`: it writes `image-test/.composed/<name>.json` and prints the `generate_image.py` command without calling the API. Inspect that JSON — confirm the references are numbered to match the images, the palette scoping in `instructions` reads correctly, and the scene negatives are present — then re-run without `--dry-run`. The image lands in `image-test/`; pass `--out-dir images` only when you already know it is a final, publish-ready asset.

### Step 6 — Evaluate and refine (bounded loop)

Do **not** stop at the first draft — validate it. Following `.claude/commands/references/evaluate.md`:

1. **Read the generated image back** with the Read tool (`image-test/<name>.jpg`, or the latest `-vN`).
2. **Evaluate it** against the brief **and** the reference images you chose in Step 3 — hold all three in context. Walk the defect checklist (style/palette, likeness/canon, brief content, composition/count) and assign a verdict: `accept` / `refine` / `flag`.
3. **`accept`** → done; carry this image and verdict to Step 7.
4. **`refine`** and you have used fewer than 3 refine passes → re-run the composer with a targeted correction, feeding the **immediately prior** image back as a likeness reference:

   ```bash
   python3 scripts/compose_image_prompt.py --request image-test/.composed/<name>-request.json \
     --correction "<specific fix — name the defect and the desired state>" \
     --prior image-test/<prev>.jpg
   ```

   It writes a versioned `image-test/<name>-vN.jpg` (first refine → `-v2`) and the matching composed JSON, never clobbering the base. Read the new image back and re-evaluate. Loop.
5. **At the cap (~3 passes)** → stop, **accept the best image so far**, and set verdict `flag`. Some defects (e.g. Paxton's left/right divine-mark side, shield-on-arm-vs-leg — see `dev/house-style-injection.md`) often will not correct no matter the wording; don't burn the whole budget on them — flag for a human instead.

### Step 7 — Report / return

Return the result object for the final (or best) image:

```json
{ "image_path": "image-test/<name or name-vN>.jpg",
  "verdict": "accept | flag",
  "notes": "what was judged, what was corrected across passes, what (if anything) remains" }
```

Print the `image_path` and remind the user to:
1. **Review** the image (style, palette, likenesses, content).
2. **Publish it if wanted** by moving the file from `image-test/` into `images/` (only `images/` is synced to the server) and adding it to the entity's `images.gallery` (or `images.hero`) in **its kb frontmatter** — include a `subjects:` list of the slugs depicted — then running `python3 scripts/build_index.py` to regenerate `config/image-map.yaml` and `config/subject-index.yaml`. Do **not** hand-edit `config/image-map.yaml` (it is generated). This skill does not auto-publish; `/export-kb` copies only mapped images to the site.

The returned object is what a calling command (e.g. a future `illustrate-session`) collects — it gives the caller a validated path plus the verdict/notes without paying the cost of re-reading the candidate images.

---

## Example

**Brief:** "Roderic faces the inquisitor Voss across a guttering lamp in the imperial tunnels beneath Aurelion — a tense parley, no violence." characters: Roderic; location: Aurelion Tunnels.

1. Resolve: `Roderic → sir-roderic-lightbearer`, `Aurelion Tunnels → aurelion`.
2. Entries: `pcs/sir-roderic-lightbearer`, `locations/aurelion`.
3. References: Roderic is a PC → his **library plate** (`config/image/library/roderic-reference-plate.jpeg` + `roderic-reference-plate-prompt.json`); for the tunnels, the street-level view fits a cramped stone interior best (`images/aurelion-street-level.jpg` + `aurelion-street-level.json`).
4. Write the request (see schema above) with a vivid scene block and `negatives: ["no spell glow", "no monsters", "no cinematic spotlighting on people"]`.
5. `python3 scripts/compose_image_prompt.py --request /tmp/roderic-confronts-voss-request.json` → base `image-test/roderic-confronts-voss.jpg`.
6. **Evaluate:** Read the base back and judge it against the brief + Roderic's plate. Roderic kept his bright palette against the muted tunnels (good), but his shield is leaning on the floor rather than held on his arm — a fixable composition defect → verdict `refine`. Re-run feeding the base back:

   ```bash
   python3 scripts/compose_image_prompt.py --request image-test/.composed/roderic-confronts-voss-request.json \
     --correction "Roderic's shield is on his arm, not leaning on the floor" \
     --prior image-test/roderic-confronts-voss.jpg
   ```

   → `image-test/roderic-confronts-voss-v2.jpg`. Read it back: the shield is now on his arm, likeness and palette held → verdict `accept`.
7. Return `{ "image_path": "image-test/roderic-confronts-voss-v2.jpg", "verdict": "accept", "notes": "Base had the shield on the floor; one refine pass moved it to his arm. Roderic's bright palette held against the muted tunnels (composer-scoped)." }` and report the path.

---

## Background reading

- `.claude/commands/references/evaluate.md` — the evaluation guide for Step 6: what to compare, the defect checklist, known hard traps (left/right asymmetry), the verdict scale, how to write a correction, and the stopping rule. Read this before judging a generation.
- `dev/house-style-injection.md` — the injection algorithm and the five validated test modes (no-override scene, override scene, character-in-scene, multi-character group, weapons-hidden). Read this if a generation comes out wrong and you need to understand what the composer did.
- `config/image/house-style.json` — the house style the composer injects (you don't edit or copy it).
- `config/image/prompts/*.json` — the per-image spec sub-prompts (identity/canon for characters, setting/architecture for locations).

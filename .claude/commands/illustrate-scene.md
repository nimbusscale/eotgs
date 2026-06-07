# Skill: Illustrate Scene

**Purpose:** Turn ONE image brief — a moment description plus the characters present and the location — into a single generated campaign illustration that matches the house style and keeps every character looking like themselves. This is the reusable single-picture engine. Use it whenever someone wants to illustrate, draw, render, or generate a picture of a campaign scene, moment, character, or place, even if they don't say "illustrate-scene." A future `illustrate-session` command (and other tools) will call this skill once per chosen moment.

**Input:** An image brief (see below). Provided by the user, by another command, or assembled by you from a session moment. ONE picture per invocation.

**Output:** A generated image at `image-test/<name>.jpg`, plus the composed prompt at `image-test/.composed/<name>.json` (gitignored scratch). A generated scene is a *candidate*: the skill returns its path so a caller can collect it, but it does **not** publish. `images/` is reserved for publish-ready assets synced to the server; `image-test/` holds all scratch/test output. Neither is committed.

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

### Step 2 — Find each entity's image-map entry

Read `config/image-map.yaml`. For each slug, find the entry whose key **ends with** `/slug` (e.g. slug `sir-roderic-lightbearer` → key `pcs/sir-roderic-lightbearer`; slug `aurelion` → key `locations/aurelion`). The key prefix (`pcs/`, `npcs/`, `locations/`, …) is the entity type and you do not need to know it in advance — match on the suffix.

### Step 3 — Select the reference image per entity

Each entry has `hero`, `gallery`, and/or `library` items. Every item may carry a `file`, a `description`, and a `prompt` (path to its spec JSON). Choose:

- **For each character:** the item that best anchors their identity — usually the `hero`. Read the `description` fields to choose. When `weapons: hidden`, prefer a weapon-free reference if one exists (e.g. Paxton's portrait over his armed pose) — the `description` will say so.
- **For the location:** the specific view that fits the moment. A location entry often has several gallery images; read their `description`s and pick by the scene (e.g. for a scene inside the cathedral, `aurelion` → the `chryseum-interior` item, not the approach shot).

For every chosen item you need both its `file` (the reference image) and its `prompt` (the spec JSON). **If an entity has no `prompt`-linked image, you cannot use it as a reference** — skip it and flag it to the user for backfill (its `prompt` needs adding to `config/image-map.yaml`). The picture can still be generated from the remaining references plus a rich scene block.

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
      "image": "images/pcs/roderic-pose.jpg",
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
- `image`/`prompt` paths are repo-relative.
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

To check the assembled prompt **before** spending on a generation (recommended when the brief is unusual), add `--dry-run`: it writes `image-test/.composed/<name>.json` and prints the `generate_image.py` command without calling the API. Inspect that JSON — confirm the references are numbered to match the images, the palette scoping in `instructions` reads correctly, and the scene negatives are present — then re-run without `--dry-run`. The image lands in `image-test/`; pass `--out-dir images` only when you already know it is a final, publish-ready asset.

### Step 6 — Report

Print the output path (`image-test/<name>.jpg`) and remind the user to:
1. **Review** the image (style, palette, likenesses, content).
2. **Publish it if wanted** by moving the file from `image-test/` into `images/` (only `images/` is synced to the server) and adding it to the entity's `gallery` (or `hero`) in `config/image-map.yaml` — this skill does not auto-publish; `/export-kb` copies only mapped images to the site.

Return the image path so a calling command (e.g. a future `illustrate-session`) can collect it.

---

## Example

**Brief:** "Roderic faces the inquisitor Voss across a guttering lamp in the imperial tunnels beneath Aurelion — a tense parley, no violence." characters: Roderic; location: Aurelion Tunnels.

1. Resolve: `Roderic → sir-roderic-lightbearer`, `Aurelion Tunnels → aurelion`.
2. Entries: `pcs/sir-roderic-lightbearer`, `locations/aurelion`.
3. References: Roderic's hero (`pcs/roderic-pose.jpg` + `roderic-reference-plate-prompt.json`); for the tunnels, the street-level view fits a cramped stone interior best (`aurelion-street-level.jpg` + `aurelion-street-level.json`).
4. Write the request (see schema above) with a vivid scene block and `negatives: ["no spell glow", "no monsters", "no cinematic spotlighting on people"]`.
5. `python3 scripts/compose_image_prompt.py --request /tmp/roderic-confronts-voss-request.json` → `image-test/roderic-confronts-voss.jpg`.
6. Report the path; note Roderic kept his bright palette against the muted tunnels (the composer scoped it automatically).

---

## Background reading

- `dev/house-style-injection.md` — the injection algorithm and the five validated test modes (no-override scene, override scene, character-in-scene, multi-character group, weapons-hidden). Read this if a generation comes out wrong and you need to understand what the composer did.
- `config/image/house-style.json` — the house style the composer injects (you don't edit or copy it).
- `config/image/prompts/*.json` — the per-image spec sub-prompts (identity/canon for characters, setting/architecture for locations).

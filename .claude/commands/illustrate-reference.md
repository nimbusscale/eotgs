# Skill: Illustrate Reference

**Purpose:** Create a durable **reference image** for one KB entity — an establishing view of a place, or a contextual portrait of a character — that gets registered on the entity and authored as a reusable prompt spec, so every *future* illustration of (or set at) that entity stays visually consistent. Use this whenever the user wants to make a hero / gallery / library / reference image *for a specific entry* ("make a reference image for the Bonewall", "generate a hero portrait for Inquisitor Voss", "I want a reference shot of X"). This is **type-agnostic**: point it at any entity and it adapts.

**How this differs from `illustrate-scene`:** `illustrate-scene` renders a one-off narrative *moment* (named characters doing something somewhere) and stops at a scratch candidate. **This** skill produces a *canonical reference plate* of a single entity and carries it all the way through *promotion* — copying the winner into `images/`, authoring a reusable `config/image/prompts/<name>.json` spec, and registering it in the entity's frontmatter. The spec you author here is exactly what `illustrate-scene` later injects as that entity's reference. If the user wants to illustrate a *scene/moment*, use `illustrate-scene` instead.

**Shape:** two phases with a human pick in between (a skill can't pause mid-run to wait for your eyes):
- **Phase 1 — generate:** read the entry, agree on the brief interactively, generate **3 candidates per view** into `image-test/` (scratch), then **STOP** and present them.
- **Phase 2 — promote:** once the user names a winner (re-invokes naming it, or just says it), copy it into `images/`, author the durable spec, register it in frontmatter, and run the integrity gate.

**Architecture:** like `illustrate-scene`, the deterministic work lives in `scripts/compose_image_prompt.py` (house-style injection) + `scripts/generate_image.py` (the API call) + `scripts/build_index.py` (regenerates the config maps from frontmatter). A reference plate is a **character-free scene** as far as the composer is concerned: the scene-request carries `"references": []` and the `scene` block holds all the content — whether the subject is a landscape or a person. You never assemble the house style by hand.

---

## Phase 1 — Generate candidates

### Step 1 — Resolve the entity and read it

Map the name through `config/entity-aliases.yaml` to its slug, or slugify directly (lowercase, hyphens, drop articles/punctuation). Read the entity's `kb/**/*.md` page in full — its `frontmatter` `type` and its prose are the source of every visual detail in the brief. Note its existing `images:` block: an entity may already have a `hero`; you might be adding a `gallery` view, or deliberately replacing the `hero`.

### Step 2 — Agree on the brief (interactive)

Propose, then confirm with the user before generating. The entity `type` only sets **defaults** — all are overridable:

| Entity type | What it depicts | Default aspect | Default slot |
|---|---|---|---|
| **location** | establishing view(s) of the place — terrain, structure, palette | `16:9 landscape` | `hero` (lead view) / `gallery` (others) |
| **npc** | a contextual portrait (person in a fitting setting, medium shot) — see `config/image/prompts/eisen-dorn-portrait.json` | `2:3 portrait` | `hero` |
| **pc** | a contextual portrait too — *but* PCs usually use a studio identity plate (`library` slot); if that's what's wanted, follow the plate convention (`type: plate`, studio backdrop, `<id>-reference-plate-prompt.json`). Otherwise treat like an NPC portrait. | `2:3 portrait` | ask: `library` plate or `hero` portrait |
| **item / faction** | rarely needed — confirm what the user actually wants (object plate? sigil? representative scene?) before proceeding | ask | ask |

Settle with the user: **how many views**, **what each depicts**, **aspect ratio per view**, **target slot**, and **candidate count** (default **3**). For a multi-view location, name the lead view (it usually becomes the `hero`).

**Palette:** default is **grounded** — author no `house_style_overrides` palette, and the muted `WORLD_PALETTE` governs (right for the Bonewall, for Dorn, for most of the world). Reflect the subject's canonical look in the *brief prose* regardless. Only when the entity is a genuinely bright, palette-defining subject (e.g. the Chryseum's gold dome, or a strong-palette PC) do you add a `house_style_overrides.palette` block — see `config/image/prompts/chryseum-exterior.json` for that pattern. When in doubt, stay grounded.

### Step 3 — Author the scene-request brief(s)

For each view, write a scene-request JSON to `image-test/.composed/<view>-request.json`. A reference plate is character-free, so `"references": []` and the `scene` block carries everything, grounded entirely in the KB page:

```json
{
  "name": "<view-slug>",
  "type": "scene",
  "aspect_ratio": "16:9 landscape",
  "references": [],
  "scene": {
    "description": "Rich, concrete visual detail drawn from the entity's KB page — what it looks like, its materials, palette, defining features. For a portrait: the person's physicality, dress, bearing, and a fitting contextual setting.",
    "composition": "Framing / focal point / what the eye reads first.",
    "lighting": "The scene's light (e.g. flat cold overcast; one-sided working light). Omit only if you want the house-style default scene lighting.",
    "mood": "The emotional register.",
    "negatives": ["things to keep out — be specific to avoid misreads"]
  }
}
```

- `name` is the output slug → `image-test/<name>.jpg`; short, descriptive, kebab-case (e.g. `bonewall-dead-shale`, `eisen-dorn-portrait`).
- Write `negatives` defensively against likely misreads (for the Bonewall: "no lit watchtowers/Spines", "no snow", "no water"). Carry over the house-style global avoids implicitly — the composer adds them.
- This brief is **scratch**. The *durable* reusable spec is a different, richer document authored only at promotion (Phase 2, Step 2) — do not author that yet.

### Step 4 — Confirm the API key

`generate_image.py` needs `OPENAI_ACCESS_KEY`. Check it without printing it:

```bash
[ -n "$OPENAI_ACCESS_KEY" ] && echo set || echo UNSET
```

If `UNSET`, stop and ask the user to set it in this session (e.g. `! export OPENAI_ACCESS_KEY=sk-...`) before generating.

### Step 5 — Compose once, then generate N candidates

For each view, build the composed prompt **once** (dry-run), then generate the candidates from that one prompt with different output names. **Always pass `--out-dir image-test`** — the default for `generate_image.py` is `images/` (published), which we must not write to here.

```bash
# 1) Build the composed prompt (writes image-test/.composed/<view>.json):
python3 scripts/compose_image_prompt.py \
  --request image-test/.composed/<view>-request.json --dry-run

# 2) Generate the candidates (n=1 per call; vary the name). Use the size flag
#    matching the aspect: --wide (16:9), --tall (2:3), --square (1:1):
for s in a b c; do
  python3 scripts/generate_image.py \
    --prompt-file image-test/.composed/<view>.json \
    --wide --name <view>-$s --out-dir image-test
done
```

Run views in parallel (independent background jobs) when generating several. Result: `image-test/<view>-{a,b,c}.jpg`, scratch only. Confirm the composed JSON carries the injected `house_style` block and `"references": []`.

### Step 6 — Evaluate, present, and STOP

`ls -la image-test/<view>-*.jpg` to confirm N non-empty files per view. **Read each candidate back** with the Read tool and judge it against the brief + house style, per `.claude/commands/references/evaluate.md` (style/medium, disciplined palette, content adherence, and any view-specific traps — e.g. a location's "hidden ruin" actually reading as easy-to-miss; no accidental Spine-like towers). Then present the candidates **grouped by view** with a one-line verdict/notes each and a recommendation, and **stop** — let the user pick.

**Do nothing else in Phase 1** — no copy to `images/`, no `config/image/prompts/` spec, no frontmatter edits, no `build_index.py`. Verify the run stayed scratch-only: `git status --porcelain` shows no tracked-file changes (`image-test/` is gitignored). If none of the candidates satisfy, offer to regenerate (new seeds) or to adjust the brief and re-run — don't promote a weak image.

---

## Phase 2 — Promote the winner

Triggered when the user names the winning candidate(s) (a re-invocation naming them, or just "promote `<view>-c` as the hero"). For each winner:

### Step 1 — Publish the image

```bash
cp image-test/<view>-<x>.jpg images/<name>.jpg
```

`<name>` is the durable slug (drop the `-a/-b/-c` candidate suffix), e.g. `images/bonewall-dead-shale.jpg`. Only `images/` is synced to the server.

### Step 2 — Author the durable prompt spec

Write `config/image/prompts/<name>.json` — a **rich, reusable sub-prompt** describing the entity's canonical look, modeled on the existing specs (locations: `chryseum-exterior.json`; portraits: `eisen-dorn-portrait.json`). This is **not** the scratch scene-request — it is the document `illustrate-scene` will later inject as this entity's reference, so it must read as a standalone canon description (title, purpose, subject/setting, composition, lighting, mood, palette or `color_palette`, `do_not_include`, `aspect_ratio`). Make it match the winning candidate, and grounded in the KB page. Use the per-type naming convention: a PC studio plate is `<id>-reference-plate-prompt.json`; a portrait is typically `<id>-portrait.json`; a location view is `<id>.json` or `<id>-<view>.json`.

### Step 3 — Register it in the entity frontmatter

Edit the entity's `kb/**/*.md` frontmatter `images:` block. `hero` is a single mapping; `gallery`/`library` are lists. Include `file`, a caption/alt + `description`, the `prompt:` pointer, and `subjects:`:

```yaml
images:
  hero:
    file: <name>.jpg
    alt: <short label>
    description: <one line — what it shows and when to use it>
    prompt: config/image/prompts/<name>.json
    subjects:
    - <entity-id>
  gallery:
  - file: <other>.jpg
    caption: <short label>
    description: <one line>
    prompt: config/image/prompts/<other>.json
    subjects:
    - <entity-id>
```

`subjects:` means "this image is a usable reference for entity X." Tag the entity's own id. (`library` `file`s are repo-root-relative, e.g. `config/image/library/…`; `hero`/`gallery` `file`s are bare names resolved under `images/`.)

### Step 4 — Regenerate the config maps and verify

```bash
python3 scripts/build_index.py          # regenerates entity-aliases / image-map / subject-index
python3 scripts/build_index.py --check   # integrity gate — must pass
```

Confirm the new entry appears in `config/image-map.yaml` and `config/subject-index.yaml`. **Never hand-edit those files** — they are generated from frontmatter.

**Publishing stays separate.** This skill stops at the integrity gate. The site and Foundry compendium update only when the user runs `/export-kb` (which also rebuilds the compendium — and Foundry needs a world relaunch to show the new pack).

---

## Guardrails (recap)

- Phase 1 is **scratch-only**: everything lands under gitignored `image-test/`; nothing touches `images/`, `config/`, or `kb/` until the user picks.
- Always `--out-dir image-test` when generating (the script default is the published `images/`).
- A reference plate is `"references": []` — the subject lives in the `scene` block.
- Grounded palette by default (no `house_style_overrides`); only bright, palette-defining subjects get an override.
- Never hand-edit the generated config maps; edit frontmatter and run `build_index.py`.
- Run `build_index.py --check` after promotion; it must pass.

## Background reading

- `.claude/commands/illustrate-scene.md` — the sibling single-moment skill and the shared composer/generate mechanics; reference selection lives there.
- `.claude/commands/references/evaluate.md` — the defect checklist and verdict scale for Step 6.
- `config/image/prompts/chryseum-exterior.json` — template for a rich **location** spec (with a bright-subject palette override).
- `config/image/prompts/eisen-dorn-portrait.json` — template for a grounded **character portrait** spec.
- `config/image/house-style.json` — the house style the composer injects (you don't edit or copy it).
- `dev/house-style-injection.md` — the injection algorithm, if a generation comes out wrong.

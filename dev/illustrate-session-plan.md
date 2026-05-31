# Plan: `/illustrate-session` — generate consistent session illustrations

> **Status: prerequisites done, ready to execute Phases 2–5.** PC reference images ✅ and the
> consistency-technique spike ✅ are both complete (committed canon now lives in
> `config/image/prompts/`). Phase 1 is done. See "Sequencing & status".

## Context

The transcript pipeline (`/extract-session` → `/incorporate-session` → `/export-kb`) currently
produces text only. Images for the published Quartz site are created ad hoc with
`image/request.py` and hand-wired into `config/image-map.yaml`. We want a repeatable step,
run **after `/incorporate-session` and before `/export-kb`**, that reads a finished session
entry, picks the session's strongest visual moments, generates illustrations through
DigitalOcean's inference service, and wires them onto the session's published page by default —
after which the user reviews the rendered images and iterates with Claude Code.

A central requirement is **visual consistency across sessions**: when Garland (or any recurring
PC/NPC/location) appears in images from different sessions, he should look the same. The DO
inference API is **text-to-image only** (`POST /v1/images/generations`, output ≤ ~1 MP /
1024×1024) — it cannot accept reference images for generation. But it *does* support vision
(VLM) input for analysis (`POST /v1/chat/completions` with `image_url`). And `/illustrate-session`
runs as Claude, which can view images directly via the Read tool. So consistency is achieved by
deriving a reusable **textual "visual canon"** for each recurring entity from its library
reference image once, caching it, and injecting it into every scene prompt that features it.

Two pieces of housekeeping ride along. The image generator lives in an accidentally-created,
gitignored `image/` directory; it should move into `scripts/` like every other pipeline tool.
And the generator must authenticate with `SANDBOX_MODEL_ACCESS_KEY` (the user's sandbox key,
separate from the `MODEL_ACCESS_KEY` used for customer work).

## Sequencing & status

This is a design doc to resume later, not an execution checklist for right now. **Prerequisites are
now done** (PC reference images ✅ and the consistency-technique spike ✅ — see below); the next step
is to execute Phases 2–5 (Phase 1 already done).

### Prerequisite (DONE): PC reference images

~~Phase 3 derives canon from each entity's library reference image, and the map had no PCs.~~
**Resolved in an earlier session (verified 2026-05-31):** `config/image-map.yaml` now has `pcs/`
entries with hero + gallery images for all four PCs — `pcs/castor`, `pcs/garland-yn-greenholt`,
`pcs/paxton-lumnus`, `pcs/sir-roderic-lightbearer` (files under `images/pcs/`). Phase 3 can derive
canon from real images. **Caveat (from the spike):** Roderic's mapped library images
(`roderic-pose.jpg`, `roderic-horse.jpg`) are a glossy, internally-inconsistent epic-hero look — do
NOT author his identity from them; use the validated spike seed instead (see canon caveat below).

### Prerequisite (DONE): consistency-technique spike

The character/house-style consistency spike (`dev/spike-character-consistency.md`) is **complete**.
It proved cross-session consistency is achievable by **text alone** (identity, two-subject no-bleed,
setting, and full character-in-setting composite all hold) and produced committed, reusable canon:

- **`config/image/prompts/house-style.json`** — the global house-style block. Load this as the style
  layer for every scene (Phase 4 step 2 — supersedes deriving style ad hoc from old specs).
- **`config/image/prompts/canon/{garland-yn-greenholt,sir-roderic-lightbearer,aurelion}.json`** —
  validated canon in the Phase-3 shape (`appearance`/`setting`, `critical_clauses`, `do_not_drift`,
  validated-seed pointers). These seed `canon/` directly — no re-derivation needed.

**Techniques to bake into Phase 4 (proven in the spike):** structured-JSON canon (not prose);
two-layer prompts (house-style verbatim + per-entity canon injected); a `subjects` array with
explicit placement + "ONLY this figure has X" + bleed-naming `do_not_include` for multi-entity
scenes; an adversarial judge that reads features off the refs itself (never pre-fed the author's
description) with human overrides passed as known departures; and a **human/own-eyes gate as the
final authority** (the judge over-fires and produces false *fails*). Recurring fixes: positively
light deep-set eyes (frontal fill); clean-shaven needs positive+negative clauses; the stubborn
cloth-arming-skirt is beaten by a **re-roll**, not more prompt words.

**Canon caveats / still TODO (later session):** Roderic's canon is `status: needs_refinement` (usable,
but the user wants one more pass) and is sourced from the spike seed, NOT the glossy player refs.
Canon for **Castor, Paxton, and recurring NPCs** is not yet authored — mechanical now via the proven
recipe; Phase 3 authors it on first use.

So: return here and execute **Phases 2–5** (Phase 1 done). No discovery work remains — only build-out.

## Locked-in decisions

- **Command name:** `/illustrate-session` (new file `.claude/commands/illustrate-session.md`).
- **Placement on the page:** hero + gallery. The **hero is a deliberate session-overview
  establishing image** representing the session's dominant theme/turning point — *not* merely the
  best of the event images. The gallery holds 3–5 specific event scenes.
- **Specs committed** to `config/image/prompts/`; existing specs move there too.
- **Visual canon committed** to `config/image/prompts/canon/<entity-slug>.json`, reused every session.
- **Generated `.jpg`s** stay in repo-root `images/` (gitignored, synced by `build_site.py`).
- **Filenames:** `session<N>-<scene-slug>.jpg` (hero `session<N>-overview.jpg`).
- **Consistency mechanism:** text visual-canon injection (image-input generation isn't offered by
  the provider). Curated library images remain the source the canon is written from — and are ready
  to feed a reference-capable provider (gpt-image edits / IP-Adapter) if one is added later.

## Phase 1 — Move & adapt the generator script ✅ DONE

`image/request.py` was moved to `scripts/generate-image.py` (now tracked) and adapted:

- **Env var:** reads `SANDBOX_MODEL_ACCESS_KEY` instead of `MODEL_ACCESS_KEY`; missing-key error
  message updated, stale `image/curl.sh` reference dropped.
- **Default out-dir:** `SCRIPT_DIR` replaced with `REPO_ROOT = Path(__file__).resolve().parent.parent`
  and `DEFAULT_OUT_DIR = REPO_ROOT / "images"`, so files land where `build_site.py` syncs from.
- **Docstring/usage:** example paths and env-var name updated.
- Everything else (DO endpoints, `openai-gpt-image-2`, `--prompt-file` JSON-passed-whole,
  `--name`/`--tall`/`--wide`/`--square`, LLM-naming fallback, b64/url handling) unchanged.

## Phase 2 — Relocate existing specs & clean up

- Create `config/image/prompts/`. Move current specs there: `image/prompts/beaconhold_map_spec.json`
  → `config/image/prompts/`, and `image/prompts/old/` → `config/image/prompts/old/` (preserve archive).
- Delete the now-empty/stray `image/` directory (also holds `__pycache__` and, transiently, a
  duplicate `kingdom-of-beaconhold-map.jpg` already present in `images/`).
- Remove the now-vestigial `image/` line from `.gitignore` (keep `images/`). Confirm
  `config/image/prompts/` is tracked (it is — not matched by the `image/` pattern).

## Phase 3 — Visual-canon reference library (consistency subsystem)

> **Spike seeded this (2026-05-31).** `config/image/prompts/canon/` already holds validated
> `garland-yn-greenholt.json`, `sir-roderic-lightbearer.json` (de-glossed, `needs_refinement`), and
> `aurelion.json`, plus the global `config/image/prompts/house-style.json`. Reuse these as-is; author
> the rest (Castor, Paxton, NPCs) with the same recipe. Roderic's canon must be sourced from the spike
> seed, not his glossy player refs (`DO_NOT_USE_AS_SOURCE` is recorded in the file).

This is the heart of cross-session consistency. A canon descriptor is a small structured JSON
capturing an entity's **generation-ready appearance**, authored once and reused.

- **Location:** `config/image/prompts/canon/<entity-slug>.json` (slug matches the KB filename /
  `entity-aliases.yaml`, e.g. `garland-yn-greenholt.json`, `bonewall.json`).
- **Shape (use the spike's validated shape — richer than the original sketch).** Match the three
  committed canon files (`garland-yn-greenholt.json`, `sir-roderic-lightbearer.json`, `aurelion.json`)
  as templates. A canon file carries:
  - `name`, `slug`, `entity_type` (`pc`/`npc`/`location`), `status` (`validated` | `needs_refinement`
    | `text_only`), `source_image`, `validated_seed` (the realized image this canon reproduces),
    `derived_from`.
  - `appearance` (characters): `face`, `ears`, `hair`, `beard`/facial-hair, `build`, `attire`,
    `signature_items`. **Locations** use `setting` instead: `architecture` (stacked eras),
    `landmarks`, `materials`, `layout_grammar`, `populace_atmosphere` — plus `scene_recipes` (proven
    camera/composition blocks) and a `judge_note`.
  - `critical_clauses` — **the diagnostic fixes that must ride on every prompt for this entity** (e.g.
    eye-lighting, clean-shaven belt-and-suspenders, the cloth-skirt re-roll note). These are the
    spike's hard-won per-entity learnings; do not drop them.
  - `human_overrides` — explicit, authoritative departures from the reference (e.g. Roderic's
    clean-shaven + no-tabard). Recorded so judges treat them as intended, not drift.
  - `do_not_drift` — the per-entity exclusion list (the things the model keeps getting wrong).
  - `multi_subject_notes`, `style_notes`, and (where the refs are bad) a `DO_NOT_USE_AS_SOURCE`
    pointer. **Rendering is NOT in the canon** — it lives once in the global
    `config/image/prompts/house-style.json`; canon is identity/setting only.
- **How canon is sourced (Claude-driven, no extra API needed):** for an entity that lacks a canon
  file, locate its **canonical reference image via `config/image-map.yaml`** (the entity page's
  `hero`, else first gallery image), **Read that image** plus any existing portrait spec in
  `config/image/prompts/old/`, and author the descriptor **feature-by-feature from what is actually
  depicted** (the spike's M2 lesson: author against the ref per feature, don't paraphrase a vibe — a
  vague "stubble" got amplified into a full beard).
  - **WATCH FOR BAD REFERENCES (spike lesson).** Some mapped library images are off-style or
    internally inconsistent and will poison the canon if copied literally — e.g. Roderic's
    `roderic-pose.jpg`/`roderic-horse.jpg` are a glossy epic-hero look (white surcoat skirt + gloss
    plate) that recreates gloss + cloth-skirt drift. When a ref conflicts with the house style or with
    itself, keep only the stable identity bits (face, heraldry) and record the rest as a
    `human_override` + `DO_NOT_USE_AS_SOURCE` pointing at a validated seed instead. Surface such
    conflicts to the user.
  - For entities with **no library image yet**, author canon from the `kb/pcs|npcs/` text description
    and set `status: text_only` (refine once an image exists).
  - **Automation fallback (documented, not required):** the same description can be produced
    headlessly via DO's VLM endpoint — `POST /v1/chat/completions` with
    `{"type":"image_url","image_url":{"url":"data:image/jpeg;base64,…"}}` on a vision model
    (`nemotron-nano-12b-v2-vl`, `kimi-k2.6`, or `openai-gpt-4o-mini`). Optionally add a small
    `scripts/describe-image.py` later; out of scope for the first cut since Claude reads images directly.
- **Already seeded by the spike (reuse as-is, do NOT re-derive):**
  `config/image/prompts/house-style.json` (global), and `canon/garland-yn-greenholt.json`,
  `canon/sir-roderic-lightbearer.json` (`needs_refinement`), `canon/aurelion.json`.
- **Seeding the rest:** the existing portrait specs (Eisen Dorn, Severin, Brenn, Triune, Mayliss)
  already are canon text — convert/import them into `canon/` rather than re-deriving. Author Castor,
  Paxton, and recurring NPCs on first use via the recipe above.

## Phase 4 — The `/illustrate-session` command

New file `.claude/commands/illustrate-session.md`, in the existing command house style (markdown
headings, `## Workflow`, `### Step N —`, `python3 scripts/...` calls, context-efficient reads).
Workflow it encodes:

1. **Locate & read the session** at `kb/sessions/*/session-N.md`. `## Summary` + `## Major Events`
   drive scene selection; `## Recap-Teaser` informs the overarching theme.
2. **Load the global house style** from `config/image/prompts/house-style.json` (the spike's validated
   M0 block — painterly photoreal, documentary/war-photography tone, post-imperial melancholy, muted
   earthen palette, anti-heroic). Inject its `medium`/`palette`/`lighting`/`tone`/`avoid` **verbatim**
   as the `style` layer of every scene spec. Do NOT re-derive style ad hoc from `old/` specs — house
   style governs all images; per-entity canon defines identity only.
3. **Select scenes:** **1 hero** = a session-overview establishing image of the whole session's
   theme/turning point (driven home as its own deliberate prompt, not a pick of the event shots);
   **3–5 gallery scenes** = the most cinematic, distinct event moments.
4. **Resolve entities & canon:** for each scene, detect the PCs/NPCs/locations present from the
   `[[wiki-links]]` in its source events (resolve via `config/entity-aliases.yaml`). For each, load
   its `config/image/prompts/canon/<slug>.json`; if missing, author it per Phase 3 (Read the library
   image) and cache. **Inject each present entity's `appearance`/`setting` canon into the scene spec**,
   and carry the entity's `critical_clauses`, `human_overrides`, and `do_not_drift` into the spec too
   (these are the per-entity fixes — e.g. eye-lighting, clean-shaven — that keep the look on-model).
   This is what keeps Garland consistent session to session.
5. **Author JSON scene specs** in the established structure (`title`/`scene.summary`, `subject(s)`,
   `setting`/`location_canon`, `lighting`, `color_palette`, `composition`, `mood`, `style` (= the
   global house-style block, verbatim), `aspect_ratio`, `do_not_include`, `details`). Save to
   `config/image/prompts/session-N/<scene-slug>.json` (hero → `overview.json`). **Spike-proven
   authoring rules:**
   - **Multi-entity scenes → a `subjects` array (prevents attribute bleed).** When 2+ characters
     share a frame, cast each as a named, **explicitly placed** entry (LEFT/RIGHT/etc.) with
     `"ONLY this figure has X"` qualifiers for its distinguishing markers (pointed ears, beard, plate),
     **plus** a `do_not_include` block that names the bleed directly (e.g. "the young knight must have
     NO beard, NO pointed ears; the old elf must NOT wear plate"). This produced ZERO attribute bleed
     across the M3 two-shot and the M5 character-in-city composite — no reference image, no inpainting.
   - **Eye-lighting clause on every face.** Deep-set eyes default into brow shadow and lose their
     diagnostic color; add the entity's `critical_clauses.eye_lighting` (soft warm frontal fill, head
     level-to-slightly-raised). Phrase lighting/pose **positively** ("soft even overcast fill", "hands
     hang loose, candid") — negative/flatness demands backfire (spike M1).
   - **Carry `human_overrides` and `do_not_drift` into the spec's `do_not_include`** so the model
     doesn't reintroduce a known wrong feature (Roderic's beard/tabard/gloss).
   - **Hero composite tip (M5):** to place figures in a cityscape, stand them on a flat overlook/
     terrace rather than forcing them onto stair treads or busy geometry (that broke perspective in
     M5 R2). Use a location's `scene_recipes` block where one exists.
6. **Generate each image** with an explicit `--name` (guarantees `session<N>-` prefix, overwrites
   cleanly, skips the LLM-naming call):
   ```bash
   python3 scripts/generate-image.py \
     --prompt-file config/image/prompts/session-N/<scene>.json \
     --name session<N>-<scene-slug> --out-dir images --wide
   ```
   `SANDBOX_MODEL_ACCESS_KEY` must be in the environment (the script errors with guidance if not;
   the command must not hardcode the key). Default `--wide` (scenes/composites/cityscapes); `--tall`
   for single-figure portrait moments.
7. **Quality-check each image (the spike's judge + own-eyes + human gate).** Do NOT trust a generation
   blind:
   - **Adversarial judge (optional but recommended for hero/recurring-character shots).** Spawn a
     fresh, skeptical judge subagent given the candidate + the entity's `validated_seed`/library
     refs, told to **read each feature category off the refs itself and flag anything added/removed**
     — never pre-fed the author's feature description (a pre-fed judge validates the author's errors;
     spike M2). Pass `human_overrides` as known intended departures so they aren't re-flagged.
   - **Own-eyes gate (always).** The orchestrator Reads the candidate and compares it feature-by-
     feature to the refs before accepting — the judge and author share blind spots.
   - **Human is the final authority.** The judge is tuned to avoid false *passes*, so it over-fires
     and produces false *fails* (M5 R1 scored low on a misread sword-hanger). Surface the image to the
     user; their call wins.
   - **Re-roll, don't prompt-pile, for stubborn variance.** Some defects (e.g. Roderic's cloth
     arming-skirt) are generation variance that more prompt words REDUCE but don't eliminate — just
     re-run the same spec a time or two. Budget for it rather than over-constraining the prompt.
   - **If a recurring look is wrong (not just this scene), fix the entity's `canon/<slug>.json`**, not
     just the scene spec — that propagates the fix to every future session.
8. **Wire into the page:** add a `sessions/<arc>/session-N` key to `config/image-map.yaml` with
   `hero:` = overview (with `alt`) and `gallery:` = event scenes (each with a `caption` naming the
   event). No `build_site.py` change needed — it already keys on the full nested KB path and depth.
9. **Report & hand off:** list specs + images; tell the user to review the `.jpg`s in `images/`.
   Document the iteration loop: to redo one image, edit its scene spec (or the entity's canon file to
   fix a recurring look) and re-run step 6 for just that file; `/export-kb` publishes the image-map.

## Phase 5 — Documentation

- `CLAUDE.md`: add `/illustrate-session` to the command list and pipeline ordering (after
  `/incorporate-session`, before `/export-kb`); note the `config/image/prompts/` and `canon/` layout.
- `dev/PROJECT.md`: add the command and the visual-canon convention if it documents the roster.

## Verification

1. **Script smoke test (no network):** `python3 scripts/generate-image.py --help` shows the new
   default out-dir; `env -u SANDBOX_MODEL_ACCESS_KEY python3 scripts/generate-image.py "x"` exits
   with the new `SANDBOX_MODEL_ACCESS_KEY` message; the file parses (`ast.parse`).
2. **Size sanity:** generate one image and confirm the DO model accepts `--wide` (1536×1024) given
   the ~1 MP cap; if rejected/over-downscaled, add a within-1 MP landscape preset to the script and
   use it as the command default. (Existing landscape images suggest `--wide` worked before — verify.)
3. **Canon consistency:** run `/illustrate-session` for Session 6
   (`kb/sessions/forgotten-and-forsaken/session-6.md`). Confirm a `garland-yn-greenholt.json` canon
   file is created/reused and that the **same appearance descriptors are injected into every Session 6
   scene featuring Garland**, and would be reused in a later session. Confirm 1 hero + 3–5 gallery
   `session6-*.jpg` in `images/`, scene specs in `config/image/prompts/session-6/`, and a new
   `config/image-map.yaml` entry.
4. **Build the site:** `python3 scripts/build_site.py` (or `/export-kb`) — session page renders a
   hero at top and a captioned `## Gallery`, with no "image source missing" warnings.
5. **Cleanup check:** `image/` is gone; `git status` shows `config/image/prompts/` (specs + canon)
   as new tracked additions; `git ls-files image/` stays empty.

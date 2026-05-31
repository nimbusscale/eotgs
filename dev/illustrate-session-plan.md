# Plan: `/illustrate-session` — generate consistent session illustrations

> **Status: design doc, not yet executed.** A prerequisite (PC reference images) must be done
> first in its own session; then return here and execute Phases 1–5. See "Sequencing & status".

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

This is a design doc to resume later, not an execution checklist for right now. The next step is a
**prerequisite handled in a separate session**, after which we revisit and execute Phases 1–5.

### Prerequisite (do first, separate session): PC reference images

Phase 3 (visual canon) derives each recurring entity's appearance from its **library reference
image**, located via `config/image-map.yaml`. Today the map covers NPCs, locations, and factions
but **no player characters** — Castor, Garland yn Greenholt, Sir Roderic Lightbearer, and Paxton
Lumnus have no reference image or `image-map` entry. Without them, canon for the party (the
entities most likely to recur across sessions) can only be authored from text, defeating the goal.

So first, in its own session: source/generate PC portrait references, drop them in `images/`, and
add `pcs/<slug>` entries to `config/image-map.yaml`. That gives `/illustrate-session` the reference
images it needs. Then return here and execute Phases 1–5.

## Locked-in decisions

- **Command name:** `/illustrate-session` (new file `.claude/commands/illustrate-session.md`).
- **Placement on the page:** hero + gallery. The **hero is a deliberate session-overview
  establishing image** representing the session's dominant theme/turning point — *not* merely the
  best of the event images. The gallery holds 3–5 specific event scenes.
- **Specs committed** to `config/image-prompts/`; existing specs move there too.
- **Visual canon committed** to `config/image-prompts/canon/<entity-slug>.json`, reused every session.
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

- Create `config/image-prompts/`. Move current specs there: `image/prompts/beaconhold_map_spec.json`
  → `config/image-prompts/`, and `image/prompts/old/` → `config/image-prompts/old/` (preserve archive).
- Delete the now-empty/stray `image/` directory (also holds `__pycache__` and, transiently, a
  duplicate `kingdom-of-beaconhold-map.jpg` already present in `images/`).
- Remove the now-vestigial `image/` line from `.gitignore` (keep `images/`). Confirm
  `config/image-prompts/` is tracked (it is — not matched by the `image/` pattern).

## Phase 3 — Visual-canon reference library (consistency subsystem)

This is the heart of cross-session consistency. A canon descriptor is a small structured JSON
capturing an entity's **generation-ready appearance**, authored once and reused.

- **Location:** `config/image-prompts/canon/<entity-slug>.json` (slug matches the KB filename /
  `entity-aliases.yaml`, e.g. `garland-yn-greenholt.json`, `bonewall.json`).
- **Shape:** e.g. `{ "name", "source_image", "appearance": { "face", "build", "hair", "attire",
  "distinguishing_features", "palette" }, "style_notes", "do_not_drift": [...] }`. Locations carry
  architecture/landscape/lighting fields instead of face/attire.
- **How canon is sourced (Claude-driven, no extra API needed):** for an entity that lacks a canon
  file, locate its **canonical reference image via `config/image-map.yaml`** (the entity page's
  `hero`, else first gallery image), **Read that image** plus any existing portrait spec in
  `config/image-prompts/old/`, and author the descriptor from what is actually depicted. Cache it.
  - For entities with **no library image yet** (e.g. some PCs), author canon from the `kb/pcs|npcs/`
    text description and flag in the file that it is text-only (to refine once an image exists).
  - **Automation fallback (documented, not required):** the same description can be produced
    headlessly via DO's VLM endpoint — `POST /v1/chat/completions` with
    `{"type":"image_url","image_url":{"url":"data:image/jpeg;base64,…"}}` on a vision model
    (`nemotron-nano-12b-v2-vl`, `kimi-k2.6`, or `openai-gpt-4o-mini`). Optionally add a small
    `scripts/describe-image.py` later; out of scope for the first cut since Claude reads images directly.
- **Seeding:** the existing portrait specs (Eisen Dorn, Severin, Brenn, Triune, Mayliss) already
  are canon text — convert/import them into `canon/` rather than re-deriving.

## Phase 4 — The `/illustrate-session` command

New file `.claude/commands/illustrate-session.md`, in the existing command house style (markdown
headings, `## Workflow`, `### Step N —`, `python3 scripts/...` calls, context-efficient reads).
Workflow it encodes:

1. **Locate & read the session** at `kb/sessions/*/session-N.md`. `## Summary` + `## Major Events`
   drive scene selection; `## Recap-Teaser` informs the overarching theme.
2. **Load house style** from one or two specs in `config/image-prompts/old/` (painterly fantasy,
   grounded, post-imperial melancholy).
3. **Select scenes:** **1 hero** = a session-overview establishing image of the whole session's
   theme/turning point (driven home as its own deliberate prompt, not a pick of the event shots);
   **3–5 gallery scenes** = the most cinematic, distinct event moments.
4. **Resolve entities & canon:** for each scene, detect the PCs/NPCs/locations present from the
   `[[wiki-links]]` in its source events (resolve via `config/entity-aliases.yaml`). For each, load
   its `config/image-prompts/canon/<slug>.json`; if missing, author it per Phase 3 (Read the library
   image) and cache. **Inject each present entity's `appearance` canon into the scene spec** (e.g. a
   `characters_present` / `location_canon` block, and weave key descriptors into `subject`/`details`).
   This is what keeps Garland consistent session to session.
5. **Author JSON scene specs** in the established structure (`title`, `subject`, `setting`,
   `lighting`, `color_palette`, `composition`, `mood`, `style`, `aspect_ratio`, `do_not_include`,
   `details`, + canon blocks). Save to `config/image-prompts/session-N/<scene-slug>.json`
   (hero → `overview.json`).
6. **Generate each image** with an explicit `--name` (guarantees `session<N>-` prefix, overwrites
   cleanly, skips the LLM-naming call):
   ```bash
   python3 scripts/generate-image.py \
     --prompt-file config/image-prompts/session-N/<scene>.json \
     --name session<N>-<scene-slug> --out-dir images --wide
   ```
   `SANDBOX_MODEL_ACCESS_KEY` must be in the environment (the script errors with guidance if not;
   the command must not hardcode the key). Default `--wide`; `--tall` for portrait-framed moments.
7. **Wire into the page:** add a `sessions/<arc>/session-N` key to `config/image-map.yaml` with
   `hero:` = overview (with `alt`) and `gallery:` = event scenes (each with a `caption` naming the
   event). No `build_site.py` change needed — it already keys on the full nested KB path and depth.
8. **Report & hand off:** list specs + images; tell the user to review the `.jpg`s in `images/`.
   Document the iteration loop: to redo one image, edit its scene spec (or the entity's canon file to
   fix a recurring look) and re-run step 6 for just that file; `/export-kb` publishes the image-map.

## Phase 5 — Documentation

- `CLAUDE.md`: add `/illustrate-session` to the command list and pipeline ordering (after
  `/incorporate-session`, before `/export-kb`); note the `config/image-prompts/` and `canon/` layout.
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
   `session6-*.jpg` in `images/`, scene specs in `config/image-prompts/session-6/`, and a new
   `config/image-map.yaml` entry.
4. **Build the site:** `python3 scripts/build_site.py` (or `/export-kb`) — session page renders a
   hero at top and a captioned `## Gallery`, with no "image source missing" warnings.
5. **Cleanup check:** `image/` is gone; `git status` shows `config/image-prompts/` (specs + canon)
   as new tracked additions; `git ls-files image/` stays empty.

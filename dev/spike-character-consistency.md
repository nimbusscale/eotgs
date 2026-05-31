# Spike: character & house-style consistency for generated images

> **Status: living doc — not started.** This is the persistent state for an exploratory spike that
> precedes building `/illustrate-session` (see `dev/illustrate-session-plan.md`). Work it **one step
> per session**, distilling each step's result into this doc so later sessions resume from the doc
> rather than re-reading every image and spec.

## How to use this doc

1. Read the **Step checklist** to find the next `TODO` step.
2. Do **only that step**. For the descriptor-derivation steps, **delegate the image/spec reading to a
   subagent** that returns only the distilled text — keep raw image bytes out of the main context.
3. Write the result into the matching **Artifacts** section below, flip the checklist entry, and stop
   for review. Don't run image generation without an explicit go-ahead — it costs API calls.

## Goal

Discover a repeatable technique that makes generated images consistent in two ways, then write the
findings back here and into `dev/illustrate-session-plan.md`:

1. **Identity consistency** — a recurring character (Garland, Roderic, …) looks like the same person
   scene to scene and session to session.
2. **House-style consistency** — every generated image reads as one art style: grounded, painterly,
   post-imperial melancholy, deliberately *anti*-heroic.

## Key decisions & constraints

- **Generation is text-to-image only.** The DO endpoint (`openai-gpt-image-2` at
  `/v1/images/generations`) does **not** take reference images as input. Consistency is carried by
  *text*.
- **Two sources of truth per asset — read both.** The **JSON spec = intent** (what was meant +
  metadata); the **generated output image = realized look/feel** (what the model actually produced,
  which may diverge from the spec). Author prompts/canon from **both**, and where they differ trust
  the realized image — it's what defines the look.
- **House style governs; references define identity only.** Player reference images fix each
  character's identity (face, build, hair, attire, heraldry), **not** rendering style. Roderic's
  reference is a glossy epic-hero outlier; he keeps his face and lion heraldry but loses the gloss.
- **Subject:** Garland (3 references, grounded — easy case) and Roderic (2 references, glossy
  outlier — hard case). Holding both should generalize to Castor/Paxton.
- **Scene (not story-bound):** the PC standing in the streets of Aurelion with Crest Aurelion and
  the golden Chryseum dome behind them. Setting is a solved problem — reuse the existing Aurelion
  specs and realized images.
- **Canon format is an open question** — test structured JSON vs. tight prose and decide empirically.

## Working method — context discipline

- **This doc is the state.** Each step distills to compact text here, not held in context.
- **Subagents do the heavy reads.** House-style and per-character identity derivation are delegated;
  the subagent returns only the descriptor text written into Artifacts.
- **Bounded review.** View only the current small generated batch (a few images), log the verdict,
  stop. Never view a large pile of outputs at once.
- **Checkpoint per step.** One step per session; stop after each, especially before generating.

## Generator usage

`image/request.py` now reads `SANDBOX_MODEL_ACCESS_KEY` (not the customer `MODEL_ACCESS_KEY`).
Run in place; write spike output to the gitignored scratch dir so the real `images/` stays clean:

```bash
mkdir -p image/spike
python3 image/request.py --prompt-file <spec.json> --name <slug> --out-dir image/spike --wide
# --tall for portrait framing; default --wide is 1536x1024
```

## Asset locations

- **Player identity references:** `images/pcs/` — Garland: `garland-portrait.jpg`,
  `garland-second-harvest.jpg`, `garland-and-castor-beaver.jpg`; Roderic: `roderic-pose.jpg`,
  `roderic-horse.jpg`.
- **House-style exemplar spec:** `image/prompts/eisen-dorn-portrait-image-spec.json`.
- **Aurelion setting specs:** `image/prompts/aurelion-street-level-image-spec.json`,
  `crest-aurelion-castle-image-spec-v2.json`, `chryseum-exterior-image-spec.json`.
- **Realized Aurelion images:** locate via `config/image-map.yaml` (`locations/aurelion`) → `images/`.
- **Character text:** `kb/pcs/garland-yn-greenholt.md`, `kb/pcs/sir-roderic-lightbearer.md`.

## Step checklist

| # | Step | Status |
|---|------|--------|
| 1 | Distill reusable house-style + Aurelion-setting block (subagent → doc) | TODO |
| 2a | Identity canon: Garland (subagent → doc) | TODO |
| 2b | Identity canon: Roderic (subagent → doc) | TODO |
| 3 | Cast each identity canon in both formats: structured JSON **and** prose | TODO |
| 4 | Generate small batches (one character/turn): format-a vs format-b, ±seeds | TODO |
| 5 | Review batch & log; iterate 4–5 until each holds across two distinct scenes | TODO |
| 6 | Finalize findings (format verdict, canon seeds) here + summary into dev plan | TODO |

## Step detail

### Step 1 — House-style + Aurelion-setting block (subagent → doc)
Subagent reads **both** the house-style exemplar spec and the Aurelion setting specs (intent) **and**
the realized Aurelion images (the actual look), and returns a compact, reusable `style` descriptor
(medium, palette, lighting, grounded/anti-heroic tone, post-imperial melancholy) plus an
Aurelion-cityscape setting block grounded in the realized images. This block rides verbatim on every
spike prompt. Write it under **Artifacts → House-style block**.

### Step 2 — Identity canon for Garland and Roderic (one char per turn)
One subagent per character reads every available asset (player reference images, any portrait spec,
the `kb/pcs/*.md` text) and returns an **identity** descriptor — face, build, age, hair, attire,
distinguishing features (Garland: elven ears, white beard, the book; Roderic: lion-heraldry shield,
cross motifs), palette — **with the reference image's rendering style stripped out** (identity, not
gloss). Include a `do_not_drift` list (e.g. Roderic: "no mirror-polish armor, no bright blue sky, no
triumphant pose"). Write under **Artifacts → Identity canon**.

### Step 3 — Two canon formats
Cast each identity descriptor in **(a)** a structured JSON appearance block (existing-spec style) and
**(b)** a tight prose paragraph. Goal: see which form the text-to-image model honors better.

### Step 4 — Generate test scenes (one character/turn) [stop before running without go-ahead]
Scene spec = house-style block + identity canon + Aurelion street setting. Generate a small batch for
one character (format-a vs format-b, a couple of seeds) into `image/spike/`. Roderic is a separate
turn. A second distinct scene/pose per character (the session-to-session proxy) and an optional
Garland+Roderic two-shot come in follow-up turns.

### Step 5 — Review batch & log
Read back **only the current small batch**. Judge: (i) identity fidelity vs the player reference,
(ii) style cohesion vs the existing Aurelion images, (iii) whether the character holds across two
distinct scenes. Log verdict + canon tweaks under **Artifacts → Findings log**, then stop. Iterate
4–5 until Garland and Roderic each read as themselves, in house style, across two scenes.

### Step 6 — Finalize
Promote the findings log to a conclusion: chosen canon format (JSON vs prose) + rationale, which
appearance fields matter, how to phrase the house-style block, how to tame an outlier like Roderic,
recommended generation flags. The refined identity descriptors here seed
`config/image-prompts/canon/` (`garland-yn-greenholt.*`, `sir-roderic-lightbearer.*`). Add a
pointer/summary into `dev/illustrate-session-plan.md`.

---

## Artifacts

### House-style block
_(Step 1 — TBD)_

### Aurelion setting block
_(Step 1 — TBD)_

### Identity canon — Garland yn Greenholt
_(Step 2a — TBD; JSON and prose variants in Step 3)_

### Identity canon — Sir Roderic Lightbearer
_(Step 2b — TBD; JSON and prose variants in Step 3)_

### Findings log
_(Steps 4–6 — append dated entries as batches are reviewed)_

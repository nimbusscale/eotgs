# Spike: character & house-style consistency for generated images

> **Status: living doc — not started.** Persistent state for an exploratory spike that precedes
> building `/illustrate-session` (see `dev/illustrate-session-plan.md`). Work it **one milestone per
> session**; each milestone iterates autonomously, then stops for human review (or a "stuck" flag).
> Distill results into this doc so later sessions resume from the doc, not from re-reading assets.

## How this runs

Each milestone is an **autonomous generate → judge → refine loop**, not a human-in-the-inner-loop
process. The human only weighs in at **milestone boundaries**:

1. Read the **Milestone checklist** for the next `TODO`.
2. Do any cheap prep (derive a canon descriptor via a subagent — text only, no generation).
3. Run the loop: generate a candidate into `image/spike/` → hand the candidate **plus** the
   reference image(s) to an **adversarial judge subagent** → apply its drift notes to the next
   prompt → repeat, governed by the **escape valve**.
4. On milestone success **or** an escape-valve halt: write the result/verdict into **Artifacts**,
   flip the checklist entry, and **stop for the human** — show the best image(s), or the stuck-flag
   (best-so-far + persistent drift + a hypothesis for a different approach).

**Orchestration:** main agent drives the loop, spawning **one adversarial judge subagent per
iteration** (raw image bytes stay in the subagent; only the verdict text returns). No Workflow.
Can be upgraded to a Workflow (parallel seeds/judges) later if convergence is too slow.

## Goal

Discover a repeatable technique that makes generated images consistent in two ways, then record the
findings here and in `dev/illustrate-session-plan.md`:

1. **Identity consistency** — a recurring character looks like the same person across scenes/sessions.
2. **House-style consistency** — every image reads as one art style: grounded, painterly,
   post-imperial melancholy, deliberately *anti*-heroic.

## Key decisions & constraints

- **Generation is text-to-image only** (`openai-gpt-image-2` at `/v1/images/generations`); no
  reference image is fed into generation. Consistency is carried by *text*.
- **Two sources of truth per asset — read both.** The **JSON spec = intent**; the **generated
  output image = realized look/feel**. Author canon/prompts from both; where they differ, trust the
  realized image.
- **House style governs; references define identity only** (face, build, hair, attire, heraldry —
  not rendering style). Roderic's reference is a glossy epic-hero outlier; he keeps face + lion
  heraldry but loses the gloss.
- **Canon format is open** — test structured JSON vs. tight prose during M1 (Garland), then lock the
  winner for M2+.
- **Subject characters:** Garland (3 refs, grounded — easy) and Roderic (2 refs, glossy — hard).
- **Setting:** Aurelion (our richest location reference set) — streets, Crest Aurelion, Chryseum
  exterior + interior.

## The adversarial judge

Every iteration is scored by a fresh judge subagent given the **candidate image + the reference
image(s)** and told to **find what's wrong** (default skeptical — a lenient "looks good" judge is the
main failure mode). It returns structured text:

- **Identity** (characters only): per-feature pass/fail — face, hair, ears (Garland), beard
  (Garland), build/age, attire, heraldry (Roderic's lion shield + cross motifs).
- **House style:** grounded vs. glossy, palette, lighting, post-imperial tone. For Roderic
  specifically: no mirror-polish armor, no bright blue sky, no triumphant hero pose.
- **Setting** (M4/M5): match to the realized Aurelion reference images.
- **Score** 0–10 + a short ranked **drift list** (the concrete things to fix in the next prompt).
- **Verdict:** `pass` only if every criterion passes and score ≥ 8.

## Escape valve (moderate)

Each iteration costs a real image-gen call + a judge's vision reads, so the loop is bounded:

- **Per-character / per-setting cap:** ~**8** generations. **Joint (M3) and composite (M5):** ~**4**.
- **No-progress halt:** stop early if the judge score does not improve for **3 consecutive** rounds.
- **Stop condition:** milestone ends on first `pass` (ideally confirmed on a second candidate) **or**
  when a cap / no-progress halt fires.
- **On halt:** do **not** keep spending. Surface best-so-far image, the persistent drift, and a
  hypothesis for a different approach; await human intervention.

## Generator usage

`scripts/generate-image.py` reads `SANDBOX_MODEL_ACCESS_KEY` (not the customer `MODEL_ACCESS_KEY`)
and defaults its out-dir to the repo's `images/`. For the spike, pass `--out-dir image/spike` to keep
candidates in the gitignored scratch dir:

```bash
mkdir -p image/spike
python3 scripts/generate-image.py --prompt-file <spec.json> --name <slug> --out-dir image/spike --wide
# --tall for portrait framing; default --wide is 1536x1024
```

## Asset locations

- **Player identity references:** `images/pcs/` — Garland: `garland-portrait.jpg`,
  `garland-second-harvest.jpg`, `garland-and-castor-beaver.jpg`; Roderic: `roderic-pose.jpg`,
  `roderic-horse.jpg`.
- **House-style exemplar spec:** `image/prompts/eisen-dorn-portrait-image-spec.json`.
- **Aurelion setting specs:** `image/prompts/aurelion-street-level-image-spec.json`,
  `aurelion-approach-image-spec.json`, `crest-aurelion-castle-image-spec-v2.json`,
  `chryseum-exterior-image-spec.json`, `chryseum-interior-image-spec.json`.
- **Realized images:** locate via `config/image-map.yaml` (`locations/aurelion`, `pcs/*`) → `images/`.
- **Character text:** `kb/pcs/garland-yn-greenholt.md`, `kb/pcs/sir-roderic-lightbearer.md`.

## Prep (cheap, no generation — do before M1)

Derive the shared **house-style block** via a subagent that reads the house-style exemplar spec, the
realized Aurelion images, and Garland's (grounded) reference, returning a compact reusable `style`
descriptor (medium, palette, lighting, grounded/anti-heroic tone, post-imperial melancholy). It rides
verbatim on every prompt. Write under **Artifacts → House-style block**.

## Milestone checklist

| # | Milestone | Loop subject | Cap | Status |
|---|-----------|--------------|-----|--------|
| 0 | Prep: house-style block (subagent, no gen) | — | — | TODO |
| 1 | **Garland solo**, plain backdrop (also: pick JSON vs prose) | identity + style | ~8 | TODO |
| 2 | **Roderic solo**, plain backdrop (de-gloss hard case) | identity + style | ~8 | TODO |
| 3 | **Garland + Roderic together**, plain backdrop | two-subject consistency | ~4 | TODO |
| 4 | **Aurelion setting alone** (no characters) | setting → realized refs | ~8 | TODO |
| 5 | **Characters in the Aurelion cityscape** | full composite | ~4 | TODO |
| 6 | Finalize findings + canon seeds + dev-plan summary | — | — | TODO |

## Milestone detail

Each of M1–M5 runs the same loop: derive any needed canon (subagent, text only) → assemble scene
spec = house-style block + canon + scene → generate into `image/spike/` → adversarial judge →
refine → repeat under the escape valve → stop for human review or stuck-flag.

- **M1 — Garland solo.** Derive Garland identity canon (subagent reads his refs + `kb` text). Cast it
  in **both** formats (structured JSON appearance block and tight prose); run a few iterations of
  each and let convergence/judge scores pick the winner — **lock that format for M2+**. Plain neutral
  backdrop so the only variables are identity + house style.
- **M2 — Roderic solo.** Derive Roderic identity canon (strip the gloss; keep lion heraldry + cross
  motifs). Plain backdrop. The judge enforces the de-gloss criteria hard.
- **M3 — Garland + Roderic together.** Plain backdrop, both in one frame; the judge checks **both**
  identities hold simultaneously (watch for attribute bleed between them).
- **M4 — Aurelion setting alone, no characters.** Derive an Aurelion setting canon from the Aurelion
  specs + realized images. Generate several shots (street/cityscape, Crest Aurelion, Chryseum
  exterior, Chryseum interior); judge against the realized Aurelion reference images for match.
- **M5 — Characters in the Aurelion cityscape.** Compose proven character canon + proven setting
  canon; the full target. Judge checks identity, house style, **and** setting match together.

## Milestone 6 — Finalize

Promote the findings log to a conclusion: chosen canon format + rationale, which appearance fields
matter, house-style phrasing that worked, how Roderic was de-glossed, recommended generation flags,
and any "couldn't crack it" notes. Refined descriptors here seed `config/image-prompts/canon/`
(`garland-yn-greenholt.*`, `sir-roderic-lightbearer.*`) and an Aurelion setting canon. Add a
pointer/summary into `dev/illustrate-session-plan.md`.

---

## Artifacts

### House-style block
_(Prep — TBD)_

### Identity canon — Garland yn Greenholt
_(M1 — TBD; JSON + prose variants, then locked format)_

### Identity canon — Sir Roderic Lightbearer
_(M2 — TBD)_

### Aurelion setting canon
_(M4 — TBD)_

### Iteration & judge log
_(M1–M5 — append dated entries: milestone, gens used, final score, verdict, key drift, outcome)_

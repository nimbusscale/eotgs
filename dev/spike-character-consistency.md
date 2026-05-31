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
- **Canon format: LOCKED to structured JSON** (decided in M1 — JSON outscored prose in both A/B
  rounds and gave tighter per-feature control over eyes and pose). Use JSON appearance blocks for M2+.
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
| 0 | Prep: house-style block (subagent, no gen) | — | — | DONE |
| 1 | **Garland solo**, plain backdrop (also: pick JSON vs prose) | identity + style | ~8 | DONE (JSON locked; pass at R1) |
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
_(Prep — DONE 2026-05-31. Derived by subagent from `eisen-dorn-portrait-image-spec.json` + realized Aurelion images + `garland-portrait.jpg`. Rides verbatim on every prompt.)_

**Prose (paste-on block):**

> Painterly photoreal concept art with a documentary tone — rendered like a war-correspondent's photograph, not a hero painting. Soft, visible brushwork over realistic form, with obsessive attention to material wear: weathered stone, oxidized metal, cracked leather, mended cloth, sun-lined skin. Palette is muted and earthen — warm limestone and ochre, tarnished amber-gold (never bright), dull steel and old iron, weathered brown leather, road-dust and slate grays, sun-bleached sage and faded green, under an overcast pewter-to-pale-amber sky. Lighting is diffuse, atmospheric, and practical: hazy overcast or a low muted golden-hour glow filtered through dust and cloud, with soft god-rays only in sacred interiors — never crisp, never high-contrast spotlighting. Tone is post-imperial melancholy and human-scale: grandeur that is faded, worn at the working surfaces, and outlived by the small tired people living in its shadow. Subjects are settled, candid, un-posed, weary. Honor the mundane. Avoid heroic gloss entirely.

**Structured (for JSON specs):**

```json
{
  "medium": "Painterly photoreal concept art with a documentary, war-photography tone; soft visible brushwork over realistic form; obsessive material-wear detail (oxidized metal, cracked leather, mended cloth, weathered stone, sun-lined skin); grounded, anti-heroic, human-scale, not a hero painting",
  "palette": [
    "warm limestone and ochre stone",
    "tarnished amber-gold, never bright or gleaming",
    "dull matte steel and old iron",
    "weathered dark-brown leather",
    "road-dust gray and slate",
    "sun-bleached sage and faded muted green",
    "overcast pewter-to-pale-amber sky",
    "weathered sun-lined skin tones"
  ],
  "lighting": "Diffuse, atmospheric, practical light — hazy overcast or a low muted golden-hour glow filtered through dust and cloud; soft volumetric god-rays only in sacred interiors; low contrast, no crisp spotlighting or dramatic shafts on people",
  "tone": "Post-imperial melancholy at human scale; faded grandeur worn down at its working surfaces and outlived by the small, tired people in its shadow; subjects settled, candid, un-posed, weary; endurance without illusion; honor the mundane over the epic",
  "avoid": [
    "heroic posing or triumphant stances",
    "glossy mirror-polish or pristine gleaming armor/metal",
    "bright saturated skies and vivid color",
    "crisp high-contrast cinematic spotlighting",
    "epic-fantasy hero gloss and idealized beauty",
    "clean matching equipment with no wear",
    "drawn-weapon battle tension",
    "youthful vigor where age and wear belong"
  ]
}
```

### Identity canon — Garland yn Greenholt
_(M1 — derived by subagent from his 3 refs + `kb/pcs/garland-yn-greenholt.md`. Identity only; rendering handled by the house-style block. A/B format winner recorded in the iteration log below.)_

**FORMAT A — structured JSON appearance block:**

```json
{
  "appearance": {
    "face": [
      "extraordinarily old man, weathered and deeply lined",
      "sun-creased leathery skin, age spots, prominent crow's feet and forehead lines",
      "pale blue-grey eyes, alert and clear",
      "high cheekbones, gaunt but vital",
      "long straight nose, heavy expressive brow"
    ],
    "ears": "long, pointed elven ears, clearly visible (Greenholt Bloodline marker — always pointed, never rounded)",
    "hair": [
      "silver-white / pale grey",
      "shoulder-length, swept back off the face",
      "wavy and somewhat tousled/wispy",
      "thinning slightly at the temples"
    ],
    "beard": [
      "full white-grey beard, medium-long",
      "covers jaw, chin and upper lip",
      "slightly unkempt, soft and bushy",
      "matching grey moustache"
    ],
    "build": [
      "tall and rangy, broad-shouldered but lean",
      "sinewy, wiry old-man strength; veined weathered hands",
      "upright posture, vigorous despite centuries of age",
      "bearing of an old soldier — steady, unhurried, sturdy"
    ],
    "attire": [
      "worn olive/brown wool hooded cloak, draped over one shoulder",
      "round metal disc brooch clasp at the throat",
      "homespun undyed/linen-brown tunic, layered",
      "wide brown leather belt with leather straps and pouches",
      "muddy, well-traveled, earth-toned"
    ],
    "signature_items": [
      "weathered leather-bound spellbook, thick and battered, bound with cord/straps",
      "greatsword 'Second Harvest' — long double-edged blade, plain straight crossguard, worn grip",
      "note: cloak/tunic/belt are constant kit; held items (book or sword) may be absent in a given scene"
    ]
  }
}
```

**FORMAT B — tight prose:**

> An extraordinarily old man with elven features: long pointed ears clearly visible (his defining trait), and a centuries-old face that is deeply weathered, leathery and lined, with high gaunt cheekbones, a long straight nose, a heavy expressive brow, and clear pale blue-grey eyes. He has shoulder-length wavy silver-white hair swept back off his face, and a full grey-white beard and moustache, medium-long and slightly unkempt. Tall, rangy and broad-shouldered yet lean, with sinewy old-man strength, veined weathered hands, and an upright, vigorous soldier's bearing despite his great age. He wears a worn olive-brown wool hooded cloak fastened at the throat by a round metal disc brooch, over a homespun earth-toned tunic and a wide brown leather belt with straps and pouches. His signature gear: a battered leather-bound spellbook and the plain-crossguard greatsword "Second Harvest" (either may be absent in a given scene).

### Identity canon — Sir Roderic Lightbearer
_(M2 — TBD)_

### Aurelion setting canon
_(M4 — TBD)_

### Iteration & judge log
_(M1–M5 — append dated entries: milestone, gens used, final score, verdict, key drift, outcome)_

#### M1 — Garland solo (2026-05-31) · 5 generations · **format A/B → JSON wins; pass at R1**

Loop: spec (house-style block + identity canon + plain-backdrop scene) → generate `--tall` into
`image/spike/` → one adversarial judge subagent per candidate (candidate + 3 refs) → refine. Spec
files preserved alongside the images in `image/spike/` (`garland-{json,prose}-r{1,2}-spec.*`,
`garland-json-r3-spec.json`).

| Round | Candidate | Format | Score | Verdict | Notes |
|-------|-----------|--------|-------|---------|-------|
| R1 | `garland-json-r1.jpg`  | JSON  | **8** | **pass** | Eyes read pale blue; all identity markers clean. Judge nits: held spellbook + busy belt (both are *spec-requested* canon kit, not real defects). |
| R1 | `garland-prose-r1.jpg` | prose | 7 | fail | Same identity, but eyes sank into brow shadow → blue lost. |
| R2 | `garland-json-r2.jpg`  | JSON  | 7 | fail | My edit ("one hand at the belt", "a single pouch") *induced* a hand-on-belt pose + hip pouch the judge flagged. |
| R2 | `garland-prose-r2.jpg` | prose | 6 | fail | Same induced pose/pouch + dimmer shadowed eyes; read as posed/defiant. |
| R3 | `garland-json-r3.jpg`  | JSON  | 6 | fail | Clean (no props, simple belt) and dignified, but model added a left-side directional key (eyes in shadow) and a frontal "posed studio" stance. |

**Outcome:** Stopped at the no-progress halt (JSON line 8→7→6). The decline is an **artifact of my own
refinement edits**, not the format — each new instruction gave the adversarial judge a fresh thing to
police, and the judge always finds *something*. Identity and grounded house-style held in **all five**
generations.

**Findings:**
- **Format = structured JSON. Locked.** JSON ≥ prose in both rounds and controlled eyes/pose better;
  prose drifted to shadowed eyes + dramatic posing both times.
- **Identity consistency: solved by text alone.** Pointed elven ears, silver swept-back hair, full
  white beard, weathered blue-eyed face, olive wool cloak + round disc brooch — all reproduced every
  run. The Garland JSON appearance block above is validated canon.
- **House-style palette/grounding: solved.** Every image is earthen, painterly-photoreal, anti-heroic.
- **Persistent drift (carry into M2+), all in lighting/pose, not identity:**
  1. **Deep-set old eyes sink into brow shadow**, killing the diagnostic blue. Must *positively light
     the eyes* — e.g. "soft frontal fill on the face; pale-blue irises catching the light." The one
     round that nailed eyes (R1) had even, slightly warm light.
  2. **Model defaults to a directional key + frontal "posed studio" portrait.** Asking for "fully
     flat diffuse, NO directional key" **backfired** (R3 came back *more* directional). Phrase
     lighting *positively* ("soft even overcast fill") and note the realized refs are actually
     golden-hour — don't over-demand flatness.
  3. Negative/exclusion instructions are weaker than positive description here; prefer "hands hang
     loose and asymmetric, weight on one hip, candid" over "NOT akimbo, NOT posed".
- **Judge calibration note:** tell the judge which kit is *canon* (cloak/brooch/belt, optional
  held book/sword) so it stops scoring requested signature items as "unrequested props."

**Garland canon seed (chosen):** `image/spike/garland-json-r1.jpg` — the only judged pass (8),
clearest eyes, full canonical kit (spellbook + cloak/brooch/belt). Its spec is
`image/spike/garland-json-spec.json` (= the validated JSON appearance block above + house-style
block + plain-backdrop scene). Note: that scratch dir is gitignored, but the spec is fully
reconstructable from the blocks recorded in this doc. `garland-json-r3.jpg` is the runner-up (cleanest composition, but
eyes in shadow). Ranking beyond the seed pick doesn't matter — the spike's deliverable is the
technique, which holds across all rounds.

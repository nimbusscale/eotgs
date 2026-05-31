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
4. **Own-eyes gate (do NOT skip on a judge `pass`).** When the judge returns a `pass`, the main agent
   must **open the candidate itself and compare it to the reference image(s) feature-by-feature**
   (facial hair, face, hair, eyes, build, armor/garment construction, heraldry — plus the recorded
   human overrides) before calling anything done. This is a deliberate side-by-side check, not a
   "looks good" glance — a subagent judge and the orchestrator share blind spots, and in M2 both the
   judge *and* the author missed an added beard + tabard that the human caught at once. If the
   own-eyes check finds drift the judge missed, treat it as a `fail`, feed it back as a refine note,
   and keep looping. Carryover: when in real doubt about an identity feature, surface the candidate to
   the **human** before locking the seed.
5. On milestone success (judge `pass` **and** own-eyes gate clears) **or** an escape-valve halt:
   write the result/verdict into **Artifacts**, flip the checklist entry, and **stop for the human**
   — show the best image(s), or the stuck-flag (best-so-far + persistent drift + a hypothesis for a
   different approach).

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
- **For M5+, the chosen spike SEED images supersede the player-provided refs as the identity source
  (decided post-M3).** The player Roderic refs are **internally inconsistent** (the glossy
  `roderic-pose.jpg` wears a white surcoat skirt and gold-gloss plate that contradict the override
  canon), which is the root cause of the recurring cloth-arming-skirt drift. The validated spike
  seeds (`roderic-json-r4.jpg`, `garland-json-r1.jpg`, the joint `garland-roderic-json-r2.jpg`) are
  internally consistent and already bake in the de-gloss + overrides — use them, not the player refs,
  as the identity reference for M5 composites and for judging M5. (Generation stays text-only; "use
  the seed" means author/judge identity against the seed image, and reuse the seed's validated JSON
  appearance block as the prompt canon.)
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
  **CRITICAL (learned the hard way in M2): the reference images are the SOLE source of identity
  truth, and the judge must READ each feature off the refs itself.** Do NOT pre-feed the judge the
  author's feature description — a judge told what to expect validates the *author's* canon and will
  confirm its errors (in M2 it rubber-stamped a wrongly-specified beard and tabard for three rounds).
  Give the judge only the feature *categories* to check (facial hair, face/jaw, hair, eyes, build,
  armor construction — metal vs cloth, garments present/absent — heraldry) and tell it to flag
  anything **added or removed** vs the refs. **Exception:** any explicit **human override** of the
  reference (recorded in the canon, e.g. Roderic's "no tabard, clean-shaven") is authoritative — pass
  it to the judge as a known intended departure so it isn't re-flagged as drift.
- **House style:** grounded vs. glossy, palette, lighting, post-imperial tone. For Roderic
  specifically: no mirror-polish armor, no bright blue sky, no triumphant hero pose.
- **Setting** (M4/M5): match to the realized Aurelion reference images.
- **Score** 0–10 + a short ranked **drift list** (the concrete things to fix in the next prompt).
- **Verdict:** `pass` only if every criterion passes and score ≥ 8.

## Escape valve (moderate)

Each iteration costs a real image-gen call + a judge's vision reads, so the loop is bounded:

- **Per-character / per-setting cap:** ~**8** generations. **Joint (M3) and composite (M5):** ~**4**.
- **No-progress halt:** stop early if the judge score does not improve for **3 consecutive** rounds.
- **Stop condition:** milestone ends on the first `pass` that **also clears the own-eyes gate**
  (step 4) — ideally confirmed on a second candidate — **or** when a cap / no-progress halt fires. A
  judge `pass` alone is not done; the orchestrator must eyeball it against the refs first.
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
| 2 | **Roderic solo**, plain backdrop (de-gloss hard case) | identity + style | ~8 | DONE (JSON; pass at R4. De-gloss easy; the lesson was the *rubric* — judge must read identity off the refs, not the author's description) |
| 3 | **Garland + Roderic together**, plain backdrop | two-subject consistency | ~4 | DONE (pass at R2; both identities hold with ZERO attribute bleed. Residual: knight's lower-body cloth arming-skirt recurs ~3/4 seeds — a single-figure Roderic-armor variance, not a two-subject problem) |
| 4 | **Aurelion setting alone** (no characters) | setting → realized refs | ~8 | DONE (2 gens; pass at R1, confirmed R2. Setting consistency solved by text alone — same recipe as identity; no de-gloss fight. Seed `aurelion-downhill-r2.jpg`: reverse-angle downhill plate, clear stairs for M5) |
| 5 | **Characters in the Aurelion cityscape** | full composite | ~4 | DONE (2 gens; R1 locked as seed by HUMAN override of a strict judge `fail`. Full composite — identity + house style + setting — holds by text alone in ONE shot. Both M5 drifts were setting/armor nits, not identity; zero attribute bleed. Seed `garland-roderic-aurelion-m5-r1.jpg`) |
| 6 | Finalize findings + canon seeds + dev-plan summary | — | — | DONE (conclusion written below; committed canon seeded to `config/image/prompts/` — house-style.json + canon/{garland,roderic,aurelion}; `dev/illustrate-session-plan.md` updated. Roderic flagged `needs_refinement`; Castor/Paxton canon deferred to a later session) |

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
  **Identity source = the spike SEED images, NOT the player refs** (see Key decisions): judge
  identity against `garland-roderic-json-r2.jpg` (and the solo seeds `roderic-json-r4.jpg` /
  `garland-json-r1.jpg`), since the player Roderic refs are internally inconsistent and reintroduce
  the cloth-skirt + gloss drift.

## Milestone 6 — Finalize (DONE 2026-05-31)

**The spike succeeded: cross-session visual consistency is achievable by TEXT ALONE.** The DO API is
text-to-image only (no reference image at generation), and the question was whether a recurring
character/location can be held consistent by injecting a reusable textual canon into every prompt. It
can — proven across 12 generations and 5 milestones: identity (M1/M2), two subjects with zero
attribute bleed (M3), setting (M4), and the full character-in-setting composite (M5).

### Committed deliverables (the spike's output, now in the repo)

- **`config/image/prompts/house-style.json`** — the global house-style block (M0). Rides verbatim on
  every prompt; controls medium/palette/lighting/tone + an `avoid` list. *House style governs;
  per-entity canon defines identity only.*
- **`config/image/prompts/canon/garland-yn-greenholt.json`** — validated PC identity canon.
- **`config/image/prompts/canon/sir-roderic-lightbearer.json`** — de-glossed PC identity canon,
  marked `status: needs_refinement` (usable; user wants another pass) with an explicit
  `DO_NOT_USE_AS_SOURCE` pointer away from the glossy player refs.
- **`config/image/prompts/canon/aurelion.json`** — validated location setting canon + the proven
  reverse-angle downhill scene recipe.
- Each canon file carries `appearance`/`setting`, `critical_clauses`, `do_not_drift`, and the
  validated-seed pointer. **Still TODO in a later session:** canon for Castor, Paxton, and recurring
  NPCs (mechanical now — same recipe).

### The technique (what to reuse)

1. **Canon format = structured JSON. Locked (M1).** Beat prose for per-feature control (especially
   eyes and pose); prose drifted to shadowed eyes + dramatic posing.
2. **Two-layer prompt: house-style block (verbatim, global) + per-entity identity canon (injected).**
   The split is load-bearing — it let Roderic keep his identity while losing the player-ref gloss.
3. **Multi-subject = a `subjects` array** with explicit LEFT/RIGHT placement, "ONLY this figure has X"
   qualifiers, and a `do_not_include` block naming the bleed directly. Zero bleed in M3 and M5, no
   reference image needed.
4. **Adversarial judge methodology (the M2 deliverable).** A fresh skeptical judge per iteration, given
   the candidate + reference SEEDS and told to read each feature *category* off the refs itself and
   flag anything added/removed — NOT pre-fed the author's feature list (that validates the author's
   errors; it rubber-stamped a wrong beard+tabard for 3 rounds in M2). Pass any human override as a
   known intended departure so it isn't re-flagged.
5. **The human / own-eyes gate is the FINAL authority, and the judge over-fires.** The judge is tuned
   to avoid false *passes*, so it produces false *fails* (M5 R1 scored 6 on a misread sword-hanger +
   a composition preference; the user passed it). Treat the score as a drift-finder, not a grade.

### Which appearance fields actually matter

Diagnostic identity markers that must be pinned: **ears** (pointed vs rounded — the elf/human tell),
**facial hair** (present/absent), **hair** (color/length), **eyes** (color *and* that they're lit),
**armor/garment construction** (metal vs cloth; which garments present/absent), **heraldry/emblems**.
Held items (book/sword) are optional per-scene kit, not identity.

### Recurring drifts + the fixes that worked

- **Deep-set eyes sink into brow shadow, killing the diagnostic iris color (M1, recurs everywhere).**
  Fix: positively light the eyes — soft warm even *frontal fill*, head level-to-slightly-raised.
  Demanding flat/no-directional light BACKFIRES. Carried as a `critical_clauses.eye_lighting` on both
  PC canons.
- **Roderic defaults to a beard/stubble (M2).** Fix: belt-and-suspenders — push clean-shaven both
  positively in `face` AND negatively in `do_not_include`. One alone leaks stubble.
- **Roderic's cloth arming-skirt between the legs (M3, M5 — the one we couldn't fully crack with
  words).** From the player ref's white surcoat skirt. Escalating prompt clauses *reduce but do not
  eliminate* it — it's generation variance defeated by **RE-ROLLING**, not more words. Budget a
  re-roll or accept bare steel faulds. (Root cause: the glossy, internally-inconsistent player refs —
  hence canon sources Roderic from the validated spike seed, not the refs.)
- **Refinement edits can induce NEW defects (M1) or break geometry (M5 R2's nonsensical stair).** When
  a candidate already reads correctly, prefer it over a "more faithful" but broken refinement.

### How Roderic was de-glossed

House style did the work: matte scratched steel, tarnished (non-gleaming) lion, faded cloth, muted
low-contrast light, candid pose. The de-gloss itself was *easy from R1* — the hard part was the
*canon derivation* (author against the refs feature-by-feature, then apply human overrides) and the
*judge rubric*, not the rendering. Identity is sourced from the validated seed `roderic-json-r4.jpg`,
NOT the player refs (`roderic-pose.jpg` / `roderic-horse.jpg`), which reintroduce the gloss + skirt.

### Recommended generation flags

`python3 scripts/generate-image.py --prompt-file <spec.json> --name <slug> --out-dir images --wide`
— `--wide` (1536×1024) for scenes/composites/cityscapes; `--tall` for single-figure portraits;
quality `high` (the script default). Pass a `.json` spec (re-serialized whole as the prompt).

### "Couldn't crack it" notes

- Roderic's lower-body cloth-skirt is a **re-roll**, not a prompt problem (above).
- Forcing figures onto stair treads broke perspective (M5 R2); a flat overlook terrace at the top of
  the stair is the reliable character stage for the Aurelion downhill plate.
- Roderic's canon is `needs_refinement` per the user — expect one more iteration session for him, then
  Castor + Paxton.

### Hand-off

`dev/illustrate-session-plan.md` updated with a spike-results summary (its "PCs have no image-map
entry" prerequisite was already satisfied in an earlier session — verified). The plan is ready to
execute Phases 2–5; no discovery work remains, only build-out and per-entity canon coverage.

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
_(M2 — DONE 2026-05-31, after a correction pass. Derived from his 2 (glossy) refs + `kb/pcs/sir-roderic-lightbearer.md`, then de-glossed. Identity only; rendering handled by the house-style block. **Format: structured JSON, per the M1 lock.** Seed = `roderic-json-r4.jpg`.)_

**Two human (user) overrides of the reference — these supersede the ref images and are authoritative canon:**
1. **Clean-shaven.** Both refs read clean-shaven; early rounds wrongly wrote in "stubble" and the model amplified it to a full beard. Roderic has **no facial hair at all**.
2. **No tabard / surcoat.** The glossy standing ref does show a white cloth tabard with the cross on it, but the user's canon is **bare full plate with the Light-cross inlaid directly into the steel breastplate** — no cloth garment over the torso. (User confirmed 2026-05-31.)

**Validated JSON appearance block (de-glossed; clean-shaven; cross-on-plate, no tabard):**

```json
{
  "appearance": {
    "face": "a man in his late twenties to early thirties, FRESHLY CLEAN-SHAVEN with completely smooth, bare, hairless skin on the jaw, chin, cheeks and upper lip — absolutely no beard, no moustache and not even faint stubble; a smooth-shaven young knight's face; fair-skinned and handsome, the weariness carried in the eyes and expression rather than in skin scruff; strong square jaw, straight nose, faint old scar; clear pale blue eyes, wide open and well-lit, the face turned slightly UP into a soft frontal light so the pale-blue irises read clearly and brightly with no shadow pooling under the brow; a candid, weary, un-posed expression",
    "hair": "wavy, tousled blond hair, medium-short, swept back off the brow and slightly matted from the road; dirty-gold, not bright",
    "build": "tall and athletic, broad-shouldered, the solid frame of a frontline fighter; an unhurried, settled soldier's bearing",
    "armor": "a FULL PLATE harness worn over the whole torso with NO cloth garment over it — no tabard, no surcoat, no fabric draped across the chest; the breastplate, pauldrons, vambraces, gauntlets, faulds and greaves are bare DULL MATTE scratched steel, dented and field-worn, faintly oxidized and grey, with tarnished dark amber-brass trim that does not gleam; scuffed and battle-used, never polished",
    "emblem": "a single muted amber-gold cross of the Light worked DIRECTLY INTO the steel breastplate as an inlaid emblem on the metal itself (NOT printed on any cloth); small worn amber Light-cross motifs repeat as faded engraving on a pauldron and the belt",
    "cloak": "a faded, dusty deep-blue wool cloak, road-worn and frayed at the hem, hanging from the shoulders behind the plate",
    "heraldry": "a battered kite shield slung on the left arm bearing his arms — a rampant lion in tarnished amber-gold on a faded deep-blue field; the shield is scratched and dented from use",
    "held_item": "a plain longsword with a worn leather-wrapped grip, sheathed or held loosely point-down, nothing raised or brandished"
  }
}
```

**Two clauses to carry into every Roderic prompt:**
- **Clean-shaven (hard).** The model strongly defaults to giving this weathered knight a beard/stubble. Push it positively in `face` ("freshly clean-shaven, smooth bare hairless skin… weariness in the eyes not skin scruff") **and** negatively in `do_not_include` ("no beard, moustache, goatee, sideburns, stubble or five-o'clock shadow"). Belt-and-suspenders was needed; one alone leaked stubble (see R3).
- **Eye-lighting (in `composition`).** "The head is level-to-slightly-raised and the face turns toward the viewer into a soft, warm, even frontal fill light, so the light falls fully on the eyes and the deep-set sockets never drop into brow shadow — the pale-blue irises must be clearly, brightly visible." Side-effect: a slight upward/noble gaze; acceptable, watch it in joint/composite frames.

### Aurelion setting canon
_(M4 — DONE 2026-05-31. Derived by subagent from the 4 Aurelion exterior **specs** (`aurelion-approach`, `aurelion-street-level`, `crest-aurelion-castle-v2`, `chryseum-exterior`) **and** the 4 realized exterior images, trusting the image where it diverged from the spec. **Setting identity only** — rendering is the house-style block. Validated by two judged passes (8/10) that both cleared the own-eyes gate; seed = `aurelion-downhill-r2.jpg`. The judge weights approach/street/castle as the style anchors and treats the Chryseum exterior's extra polish as the sacred-building exception so a whole-city shot isn't pulled glossy.)_

**Spec-vs-image divergences resolved (image chosen):** castle facade reads more uniformly gold-trimmed and more battlemented/fortress-like than the spec's "selective maintenance, not a fortress"; Chryseum windows read warm pale gold-white, not the spec's cool blue-white; dome color is bright-warm-gold up close (chryseum-exterior) but greener verdigris-dominant at city distance (approach) — canon carries both, and the downhill cityscape uses the **distance** read (tarnished amber-and-verdigris, never bright).

**Validated JSON setting canon (identity only; rides with the house-style block, never replaces it):**

```json
{
  "city_identity": "Aurelion — a once-imperial golden city in slow decline, built up a hillside, its grandeur tarnished and patched but still functioning; honey-limestone Roman-scale bones beneath centuries of smaller, poorer construction.",
  "architecture": {
    "stacked_eras": [
      "Base: massive Imperium-era honey/pale limestone — large precisely-cut blocks, engineered walls, arched gateways, colonnades with carved capitals, weathered gilded inscriptions; the structural foundation of everything above.",
      "Middle: medieval-scale stone and brick housing — narrower, lower, less ambitious, settling unevenly on the imperial base.",
      "Top: improvised timber-frame upper stories, plaster/wattle, mismatched terracotta and gray tile roofs, lean-tos and cantilevered overhangs cramming the skyline."
    ],
    "compression": "Each layer smaller and more modest than the one below; dense tiled rooftops climb and compress up the hill, packed tightly between and atop imperial stonework.",
    "sacred_verticality": "Luciferian sacred structures break the pattern with clean verticals, soaring symmetrical proportions, radiating order — a Byzantine-domed-basilica-meets-Gothic-cathedral massing topped by a gilded dome."
  },
  "landmarks": {
    "chryseum": "The cathedral of the Light and the city's brightest, warmest focal point. A towering symmetrical limestone facade flanked by slender pinnacled buttress-towers, crowned by a large ribbed dome topped by a lantern/cupola — bright warm gold up close (faint verdigris) but read as GREENER verdigris-and-amber across the city; the warmest point in a whole-city frame but tarnished, NOT mirror-bright.",
    "crest_aurelion": "Count Marrow's seat — a pale limestone palace-vault on the highest rise, a battlemented multi-towered fortress-palace with crenellated rectangular towers and gold-trimmed cornices, ringed by cypress trees; the high vantage point for a downhill reverse-angle shot is at/just below it.",
    "city_gate": "A wide single-arched imperial gate set in long curtain walls, faintly gold-inscribed around the arch, oversized for current traffic.",
    "processional_spine": "A broad straight pale stone-paved stair-road forms the city's axis, running from the castle gates at the crown straight down through the city to the imperial gate and road at the base — cleaner and straighter than the cramped streets it cuts through."
  },
  "materials": [
    "Tarnished gold and verdigris green — never bright (except the Chryseum dome seen up close); gilded trim, inscriptions and domes gone aged amber and green-gold.",
    "Honey/pale limestone and warm sandstone — the dominant imperial stone, sun-warmed but weathered.",
    "Weathered brown timber framing, dirty plaster cream/white — the upper improvised stories.",
    "Mismatched roof tiles — terracotta, gray and patched brown patchwork.",
    "Tarnished gold-over-steel Aureate guard kit — gilded plate worn through to dull steel at stress points, mended cloaks.",
    "Stone-paved imperial roads and stairs with weeds in the cracks; moss reclaiming cracked masonry."
  ],
  "layout_grammar": {
    "site": "Built on and up a hill; dense construction layers and compresses as it climbs, castle at the crown, Chryseum dome breaking the roofline.",
    "spine": "A single dominant processional axis (castle → stair → avenue → gate → road) organizes the city and leads the eye uphill to the seats of power or downhill to the gate and open country.",
    "defenses": "Long imperial curtain walls and a wide arched gate enclose the base of the hill.",
    "hinterland": "Beyond the walls: thin, tired fields and sparse/leafless orchards, scattered patched farmsteads, rolling dry-gold countryside and low hills, threaded by the oversized old imperial stone road."
  },
  "populace_atmosphere": "Decline, not ruin — patched, tired, functioning. Chimney and hearth smoke rising throughout the rooftops; subdued, no festivity, no active destruction; Aureate patrols omnipresent rather than violent; a city that remembers being important and knows it no longer is."
}
```

**M4 reverse-angle scene block (the composition that worked — reusable as the M5 base plate):** high vantage at/just below Crest Aurelion looking DOWN and OUT; FG = top of one broad **continuous** processional stair descending away from the camera, kept CLEAR/empty (plain balustrade + cypress flanking, not funerary plinths) so M5 figures can be placed on it; MID = layered terracotta/tile rooftops + the tarnished gold-verdigris dome roughly centered, chimney smoke; BG = curtain wall + arched gate, processional road out, thin fields/orchards, low hills, overcast pewter-to-pale-amber sky with a muted golden-hour break. Full spec: `image/spike/aurelion-downhill-r2-spec.json` (gitignored scratch; reconstructable from the house-style block + the canon above + this scene block).

**Aurelion setting seed (chosen for M5):** `image/spike/aurelion-downhill-r2.jpg` — judged pass (8/10), own-eyes gate cleared: same dome/materials/gate/wall/road/fields as the realized exteriors, grounded house style with no gloss creep, and a single clear continuous foreground stair ready for M5 character placement. Runner-up: `image/spike/aurelion-downhill-r1.jpg` (also a judged pass at 8/10; dome crowded the left edge and the foreground stair was split by a central spine).

**Seed-choice nuance (user, 2026-05-31):** the judge scored R1 and R2 **equal at 8/10** on identity + house style — R2 was chosen as the M5 base plate purely on composition (centered dome, single continuous stair = a cleaner stage for figures). The **user prefers R1 as the truer picture of how they imagine Aurelion**, but is fine using R2 as the M5 basis. So: **R2 = M5 base plate; R1 = the better stand-alone Aurelion image.** Do not "correct" the M5 seed back to R1 in a later session — the split is intentional. (Both are reverse-angle shots in which Crest Aurelion itself is out of frame; if M5 work decides the castle must be visible, a flank-vantage regen supersedes this pick entirely.)

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

#### M2 — Roderic solo (2026-05-31) · 5 generations · **pass at R4 (after a canon + rubric correction)**

Loop: de-glossed Roderic identity canon (JSON) + house-style block + plain-backdrop scene →
generate `--tall` into `image/spike/` → one adversarial judge subagent per candidate (candidate + 2
glossy refs) → refine. Specs preserved alongside the images (`roderic-json-r{1,2,2b,3,4}-spec.json`).

| Round | Candidate | Score | Verdict | Notes |
|-------|-----------|-------|---------|-------|
| R1 | `roderic-json-r1.jpg`  | 8 | fail (old rubric) | De-gloss landed first try. Eyes in brow shadow. **But the canon was wrong (see below) and the old judge couldn't see it.** |
| R2 | `roderic-json-r2.jpg`  | 9 | "pass" (old rubric) | Eye-lighting clause fixed the eyes. **False pass** — beard + tabard drift uncaught because the judge was pre-fed the (wrong) feature list. |
| R2b | `roderic-json-r2b.jpg` | 9 | "pass" (old rubric) | Re-roll; same false pass. |
| — | _(user review)_ | — | — | **User caught two identity errors the rubric missed:** (1) every candidate had a full beard/moustache, but the refs are **clean-shaven**; (2) every candidate wore a cloth **tabard**, but canon is bare **full plate**, cross on the steel. |
| R3 | `roderic-json-r3.jpg`  | 6 | fail (new rubric) | Canon fixed (clean-shaven + cross-on-plate, no tabard) **and** rubric fixed (judge reads features off the refs itself). New judge promptly caught residual blond **stubble** + eyes back in shadow. |
| R4 | `roderic-json-r4.jpg`  | 7→**pass** | **pass** | Forced clean-shaven (positive *and* negative) + re-lit eyes. Clean-shaven ✓, eyes pale-blue ✓, bare plate + cross-on-steel ✓, full de-gloss ✓. New judge scored 7 only because — faithfully reading the ref — it wanted the tabard *restored*; that's the user-overridden point, so it's a **pass by canon**. **Chosen seed.** |

**Outcome:** Milestone passed at R4. 5 of ~8 generations used. The first "pass" (R2) was a **false
positive** caught by the human, which exposed the most important finding of the whole spike:

**Findings:**
- **THE RUBRIC BUG (most important).** A judge that is *told* the identity features validates the
  **author's description**, not the character. My R1–R2b judge prompt asserted "blond hair… white
  surcoat with a gold cross" as fact, so it confirmed my two canon errors (beard, tabard) and even
  rationalized the beard away ("matches the clean-shaven refs"). **Fix: the judge must treat the
  reference images as the SOLE source of identity truth and read every feature off them itself** —
  given only feature *categories* to check (facial hair, face, hair, eyes, build, armor
  construction, heraldry) and told to flag anything ADDED or REMOVED vs the refs. The corrected
  judge caught the stubble immediately. This judge methodology is the real M2 deliverable and must
  govern M3–M5. (Updated judge prompt is reflected in the agent calls; reuse it.)
- **Canon derivation is the weak link, not generation.** Both errors originated in *my* text
  ("stubble", "off-white linen surcoat"), then the model faithfully amplified them (stubble → full
  beard). Author the canon **against the refs feature-by-feature**, and have the human confirm
  identity before trusting any "pass."
- **Human overrides supersede the reference.** The user removed the tabard the refs actually show.
  Record such overrides explicitly in the canon (see the two overrides above) so later judges —
  which are told refs=truth — don't keep flagging the intended departure as drift.
- **De-gloss itself is solved by text alone and was genuinely easy** — matte steel, tarnished lion,
  faded cloth, muted light, candid pose, plain backdrop all landed from R1 and held every round.
  *House style governs; references define identity only* — confirmed.
- **Clean-shaven needs belt-and-suspenders.** The model wants to beard this weathered knight.
  Positive face phrasing alone (R3) still leaked stubble; positive + negative (R4) cleared it.
- **The M1 eye-shadow drift recurs and the M1 fix transfers** — positively light the eyes (face up,
  soft frontal fill). Generation variance can still drop them into shadow (R3), so keep the clause
  strong.

**Roderic canon seed (chosen):** `image/spike/roderic-json-r4.jpg` — the judged pass: clean-shaven
young knight, pale-blue eyes lit, bare matte full plate with the gold Light-cross inlaid in the
steel, faded blue cloak, rampant-lion-on-blue shield, point-down longsword, plain grey backdrop. Its
spec is `image/spike/roderic-json-r4-spec.json` (= the validated JSON appearance block above +
clean-shaven/eye-lighting clauses + house-style block + plain-backdrop scene), fully reconstructable
from the blocks in this doc. R1–R3 are superseded (wrong canon).

#### M3 — Garland + Roderic together (2026-05-31) · 4 generations (cap reached) · **pass at R2 (own-eyes cleared); identities hold with ZERO bleed**

Loop: single joint spec = house-style block + **both** validated identity canons (Garland's JSON
appearance block + Roderic's de-glossed JSON block w/ the two overrides) cast as a `subjects` array
with explicit LEFT(old elf)/RIGHT(young knight) placement and contrast cues, + a two-shot
plain-backdrop scene → generate `--wide` into `image/spike/` → one adversarial judge subagent per
candidate (candidate + **all 5 refs**, reading features off the refs per the M2 rubric, with
Roderic's two overrides passed as known intended departures) → refine → own-eyes gate on any pass.
Specs preserved alongside the images (`garland-roderic-json-r{1,2,3,4}-spec.json`).

| Round | Candidate | Score | Verdict | Notes |
|-------|-----------|-------|---------|-------|
| R1 | `garland-roderic-json-r1.jpg` | 7 | fail | Both identities perfect, zero bleed, grounded style — single defect: a knotted **cloth tabard-skirt** draped over the knight's lower torso/groin (override #2 violation). |
| R2 | `garland-roderic-json-r2.jpg` | **8.5** | **pass** | Strengthened armor clause (bare steel faulds, no waist cloth) cleared it. Clean bare plate, steel faulds, no cloth anywhere. **Own-eyes gate cleared** feature-by-feature vs refs. **Chosen seed.** |
| R3 | `garland-roderic-json-r3.jpg` | 7 | fail | Confirmation re-roll, **same spec as R2**: identity/bleed/style/eyes all held again, but the **cloth arming-skirt between the legs recurred** below the steel faulds. |
| R4 | `garland-roderic-json-r4.jpg` | 6 | fail | Hardened the clause further (positive: "bare steel cuisses, nothing hangs between the legs"). Cloth drape between the legs **still** read (borderline/ambiguous). Cap reached. |

**Outcome:** Milestone **passed at R2** (judged pass + own-eyes gate cleared), then the ~4-gen cap
fired while trying to land a second fully-clean confirmation. The core M3 question is answered
decisively across **all four** generations.

**Findings:**
- **Two-subject identity consistency: SOLVED by text alone, with ZERO attribute bleed in 4/4 gens.**
  Garland (pointed ears, white beard, silver hair, wool cloak + disc brooch, spellbook, no plate) and
  Roderic (clean-shaven, blond, rounded ears, matte plate, cross-on-steel, lion shield) each held
  every feature simultaneously. The young knight never inherited the elf's beard or pointed ears; the
  old elf never gained plate; they always read as two different people of different ages and races.
- **The technique that worked: a `subjects` array with explicit placement + contrast cues.** Casting
  the two validated canons as named, placed (LEFT old elf / RIGHT young knight) entries — each with
  "ONLY this figure has X" qualifiers (pointed ears, beard) and a `do_not_include` block that names
  bleed directly ("the young knight must have NO beard, NO pointed ears; the old elf must NOT wear
  plate") — was enough. No reference image, no inpainting. House style + eye-lighting clauses
  transferred unchanged from M1/M2 and held.
- **House style + eyes: held in all 4.** Grounded, matte, muted, anti-heroic; both faces lit, irises
  readable. The M1/M2 eye-lighting clause needs no change for two-shots.
- **Residual drift (the ONE stubborn thing): the knight's lower-body cloth arming-skirt.** Roderic's
  glossy `roderic-pose.jpg` ref wears a white surcoat **skirt** over the groin; the model keeps
  reaching for it and renders a cloth drape between the legs below the steel faulds. It appeared in
  R1, R3 and R4 and was only fully clean in R2. Escalating positive+negative clauses ("bare steel
  faulds/tassets/cuisses, nothing hangs between the legs, the gap shows only metal") **reduced but did
  not eliminate** it — this is generation variance on a single feature, defeated by **re-rolling**,
  not by more prompt words. NB: this is the *same* single-subject Roderic-armor quirk, surfacing
  again; it is **not** a two-subject failure. Carry into M5 and finalize: budget a re-roll or two for
  Roderic's lower body, or accept a steel faulds-skirt as close-enough.
- **Judge methodology (M2 rubric) transferred cleanly to two subjects.** Giving the judge all five
  refs + only feature *categories* (per figure) + the two overrides as known departures produced
  reliable per-figure verdicts and caught the cloth-skirt every time it appeared. The own-eyes gate
  agreed with the judge on every round (no false pass this milestone).

**M3 canon seed (chosen):** `image/spike/garland-roderic-json-r2.jpg` — the judged pass that cleared
the own-eyes gate: both identities correct and distinct, zero bleed, knight in clean bare matte plate
(steel faulds, no cloth), grounded house style, eyes lit on both. Its spec is
`image/spike/garland-roderic-json-r2-spec.json` (= house-style block + both validated identity
canons as a placed `subjects` array + two-shot plain-backdrop scene), fully reconstructable from the
blocks in this doc. R1/R3/R4 are superseded (cloth-skirt drift). Scratch dir is gitignored; the spec
is reconstructable from the recorded blocks.

#### M4 — Aurelion setting alone, no characters (2026-05-31) · 2 generations · **pass at R1, confirmed at R2 (both own-eyes cleared); first SETTING milestone**

First **setting** milestone (M1–M3 were characters). Same loop, adapted: a prep subagent derived a
structured-JSON **Aurelion setting canon** (identity only) from the 4 Aurelion exterior specs **and**
the 4 realized exterior images, trusting the image on divergence → assemble scene spec = house-style
block (verbatim) + setting canon + a **reverse-angle downhill scene block** → generate `--wide` into
`image/spike/` → one adversarial judge subagent per candidate (candidate + **all 4 realized
exteriors**, style anchored on approach/street/castle with the Chryseum's polish treated as the
sacred-building exception) → own-eyes gate on each pass. Specs preserved alongside the images
(`aurelion-downhill-r{1,2}-spec.json`).

| Round | Candidate | Score | Verdict | Notes |
|-------|-----------|-------|---------|-------|
| R1 | `aurelion-downhill-r1.jpg` | **8** | **pass** | First try. Correct high reverse vantage looking down/out; clear descending foreground stairs; tarnished gold-verdigris dome; curtain wall + arched gate + receding fields — reads as the same city, grounded house style, no gloss creep, no characters. **Own-eyes gate cleared.** Judge nits (non-blocking): dome crowded the left frame edge; foreground stair split by a central spine; flanking plinths read slightly funerary. |
| R2 | `aurelion-downhill-r2.jpg` | **8** | **pass** | Confirmation with the R1 nits folded in (center the dome, one continuous stair run, plain civic balustrade not tombs). Dome centered, single broad continuous descending stair = a cleaner M5 base plate; identity/style/no-characters all held again. **Own-eyes gate cleared. Chosen seed.** |

**Outcome:** Milestone **passed at R1** (judge pass + own-eyes gate) and **confirmed at R2**. Only 2 of
~8 generations used — the setting technique converged immediately, even faster than the character
milestones.

**Findings:**
- **Setting consistency: SOLVED by text alone, like identity.** The same recipe that carried character
  identity (text-only JSON canon + the verbatim house-style block) carried *setting* identity on the
  first generation. The derived Aurelion canon reproduced the dome (tarnished gold/verdigris, ribbed,
  lantern-topped), the three stacked eras, the imperial gate + curtain wall, the processional
  stair-spine, and the thin-fields hinterland — unmistakably the **same city** as the refs, reverse-angled, not a generic medieval town. No reference image fed to generation.
- **No de-gloss problem for the setting (as predicted).** The M0 house-style block was *derived from*
  these realized exteriors, so matching the exteriors and matching the house style were the same thing.
  The dome came back tarnished, not bright, both rounds — none of the M2/M3 gloss fight (which was a
  Roderic *player-ref* issue, not a setting one).
- **The judge's sacred-building exception mattered.** Telling the judge to anchor style on
  approach/street/castle and treat the Chryseum exterior's extra polish as the sacred exception kept
  the whole-city shot from being pulled glossy by the one ornate ref.
- **Refinement edits here were cheap and additive, not regressive** (unlike M1's score decline). R1→R2
  notes (center dome, single continuous stair, civic-not-funerary balustrade) all landed cleanly and
  improved the M5 base plate without breaking anything — a setting wide shot has more compositional
  slack than a tightly-specified portrait.
- **Composition-for-M5 is a real, separable criterion.** Both rounds passed identity+style; R2 won the
  seed purely on M5-readiness (centered dome, one clear continuous stair plane for figure placement).
  Carry into M5: the reverse-angle downhill plate with a clear stair is the intended stage for the
  Garland+Roderic composite (identity source = the M3 seed `garland-roderic-json-r2.jpg`).

**M4 setting seed (chosen):** `image/spike/aurelion-downhill-r2.jpg` — judged pass (8) that cleared the
own-eyes gate: same dome/materials/gate/wall/road/fields as the realized exteriors, grounded house
style, centered tarnished dome, and a single clear continuous foreground stair ready for M5 character
placement. Spec: `image/spike/aurelion-downhill-r2-spec.json` (= house-style block + validated
Aurelion setting canon + reverse-angle downhill scene block), reconstructable from the blocks above.
R1 (`aurelion-downhill-r1.jpg`) is the runner-up/confirmation (also a judged pass; split stair + dome
crowding the edge). Scratch dir is gitignored; specs are reconstructable from the recorded blocks.

#### M5 — Garland + Roderic in the Aurelion cityscape (2026-05-31) · 2 generations · **R1 locked as seed by HUMAN override of a strict judge `fail`; full composite holds by text alone**

The full target: compose proven character canon (M3 seed identities) + proven setting canon (M4 base
plate) into one frame. Single composite spec = house-style block + **both** validated identity canons
(as the placed `subjects` array, with the two Roderic overrides) + the M4 Aurelion setting canon + the
M4 reverse-angle downhill scene block, with the foreground stair re-tasked as the figures' stage →
generate `--wide` into `image/spike/` → one adversarial judge subagent (candidate + the M3 seed
`garland-roderic-json-r2.jpg`, solo seeds `garland-json-r1.jpg` / `roderic-json-r4.jpg`, and the M4
setting seed `aurelion-downhill-r2.jpg`; **identity source = the spike SEEDS, not the player refs**) →
own-eyes gate → **human review**. Specs preserved alongside the images
(`garland-roderic-aurelion-m5-r{1,2}-spec.json`).

| Round | Candidate | Score | Verdict | Notes |
|-------|-----------|-------|---------|-------|
| R1 | `garland-roderic-aurelion-m5-r1.jpg` | 6 | judge `fail` → **HUMAN PASS (chosen seed)** | Both identities dead-on, ZERO bleed; house style grounded; Aurelion unmistakable (centered tarnished dome, gate, curtain wall, processional road, fields); figures convincingly integrated at correct scale on a flat overlook terrace at the TOP of the stair. Judge `fail` was two non-identity nits: (1) a small dark hip-drape it pattern-matched to the M3 cloth-skirt — actually reads as a leather sword-hanger, not the white surcoat-skirt; (2) figures on the terrace rather than mid-stair (a composition preference). **Human (user) judged R1 good and overrode the strict score** — per the spike's own rule that human/own-eyes judgment is the final gate. |
| R2 | `garland-roderic-aurelion-m5-r2.jpg` | — | **fail (human)** | Refinement attempt: plant the figures ON the visible stair treads + harden the anti-cloth-skirt clause. Armor came back cleaner (bare steel faulds, no drape) and identities/style/city all held, BUT the **stair geometry was nonsense** — a lopsided curved amphitheater fan sweeping to the lower-right, disconnected from the flat scrap the figures stand on. Spatially incoherent; rejected by the user on sight. R1's coherent terrace beats R2's broken stair. |

**Outcome:** Milestone **passed at R1 by human override**, R2 rejected for broken stair geometry. 2 of
~4 gens used. The spike's central question is now answered end-to-end: **identity + house style +
setting all hold together in a single text-only generation, with zero attribute bleed, on the first
composite try.**

**Findings:**
- **THE FULL COMPOSITE WORKS BY TEXT ALONE — the spike's deliverable is proven.** Stacking the three
  validated text blocks (house style + placed two-subject identity canon + setting canon + scene) in
  one spec produced a coherent, on-model, on-style, on-setting two-character cityscape on the **first**
  generation. No reference image fed to generation; no inpainting; no compositing. Identity held (both
  figures, every feature), house style held (grounded, matte, tarnished, anti-heroic), setting held
  (unmistakably Aurelion), and the figures integrated into the scene at believable scale and lighting.
- **Zero attribute bleed persisted into the composite.** The `subjects`-array technique from M3 (named,
  placed LEFT/RIGHT entries with "ONLY this figure has X" qualifiers + a `do_not_include` block naming
  the bleed directly) carried through unchanged even with a full environment added. The young knight
  never inherited the elf's beard/ears/age; the elf never gained plate.
- **The judge over-fires on the known cloth-skirt and on composition; the human gate is essential.**
  The R1 `fail` was a strict-rubric artifact, not a real defect: the judge reflexively flagged a leather
  sword-hanger as the M3 cloth-skirt (false positive) and dinged a terrace-vs-mid-stair composition
  choice. Both are exactly the kind of plausible-but-wrong call the own-eyes/human gate exists to catch
  in the *lenient* direction — here the human RAISED a strict score rather than lowering a lenient one.
  Carry into M6: the adversarial judge is calibrated to avoid false *passes*, so it produces false
  *fails*; treat its score as a drift-finder, not a final grade, and let the human/own-eyes gate make
  the call.
- **Refinement can regress geometry, not just attributes.** R2's attempt to force figures onto the stair
  produced spatially incoherent steps — a reminder that adding a hard compositional constraint to a
  busy scene can break perspective. When R1 already reads correctly, prefer it over a "more faithful"
  but broken refinement (echoes M1's "refinement edits induce new defects" finding).
- **Identity source = spike seeds, confirmed sound.** Authoring/judging identity against the validated
  spike seeds (not the internally-inconsistent player Roderic refs) kept the cloth-skirt + gloss drift
  from being *reintroduced* — R1's only skirt-adjacent element was a minor hip-drape, far milder than
  the player-ref-driven surcoat-skirt that plagued M3.

**M5 canon seed (chosen):** `image/spike/garland-roderic-aurelion-m5-r1.jpg` — the full composite the
user accepted: both identities correct and distinct (zero bleed), grounded house style, unmistakable
Aurelion cityscape (centered tarnished dome, imperial gate, curtain wall, processional road, fields),
figures integrated at human scale with a bold gold Light-cross on bare matte plate and the blue lion
shield. Its spec is `image/spike/garland-roderic-aurelion-m5-r1-spec.json` (= house-style block + both
validated identity canons as a placed `subjects` array + Aurelion setting canon + reverse-angle downhill
scene block), fully reconstructable from the blocks recorded in this doc. R2 is superseded (broken stair
geometry). Scratch dir is gitignored; the spec is reconstructable from the recorded blocks.

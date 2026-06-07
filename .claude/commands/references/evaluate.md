# Evaluating a generated scene (and deciding whether to refine)

Read this after each generation in `illustrate-scene`'s evaluate → refine loop.
You already hold the three things good judgment needs in context, so judge inline.

## What to compare — hold all three at once

1. **The brief** (the intent): what moment, which characters, what action, what
   location, the `weapons` mode, the `negatives`.
2. **The generated image** you just Read back.
3. **The reference image(s)** — the canon likeness for each character and the
   canonical look of the location.

Holding the reference alongside the generation is what catches the
"shield strapped to his leg, not his arm" class of error — a defect you simply
cannot see if you only compare the image to the brief. Always look back at the
plate.

## Defect checklist

Walk these every time:

- **Style / medium + palette.** Painterly photoreal, grounded, material-honest —
  not glossy CGI, not movie-poster glamour. The muted world palette governs the
  environment and grounded figures; a strong-palette character (e.g. Roderic's
  bright blue-and-gold) must stay bright and **not** be muted into the
  background. A strong-palette location (e.g. the Chryseum interior) keeps its
  canonical brightness.
- **Character likeness / canon.** For each character, does the face, hair,
  build, age, armor, heraldry, and signature gear match their reference plate?
  No drift toward a generic model-handsome face.
- **Brief content.** Are the right characters present, doing the described
  action, in the right location? Is `weapons: shown/hidden` honored (in hidden
  mode, **no** weapons, shields, sheathed blades, or signature arms anywhere)?
  Are the `negatives` respected (no spell glow, no monsters, etc. when excluded)?
- **Composition & count.** Does the character count match the brief exactly? No
  duplicated or extra figures, no extra/merged limbs, no spurious crowd members
  at a focal table that should seat N.

## Known hard traps — call these out explicitly

Some defects often do **not** correct no matter how the correction is worded.
Recognize them so you don't burn all three passes chasing them:

- **Left/right asymmetric features.** Paxton's divine mark is canonically on
  **his right** (the viewer's left when he faces forward); the model frequently
  mirrors it and resists correction. This is a documented open limitation — see
  `dev/house-style-injection.md`.
- **Shield-on-arm vs. on-leg / leaning on the floor** and similar gear-placement
  swaps may be the same stubborn class.

If a defect is one of these and one correction pass doesn't take, prefer to
`flag` rather than keep spending.

## Verdict scale

- **`accept`** — adheres to the brief, references, house style; no fixable defect
  worth another generation.
- **`refine`** — a fixable defect is present; worth one more pass with a worded
  correction.
- **`flag`** — defect remains after the pass budget, or it is a known hard trap
  unlikely to correct. Accept the best image so far and hand it to a human.

## Fixable by a worded correction vs. not

- **Fixable:** a missing or extra element, wrong palette (a figure muted that
  should be bright), weapons present when they should be hidden, awkward framing
  or focal point, an extra/duplicate figure.
- **Likely not fixable:** locked-in left/right asymmetry (the divine-mark side),
  and possibly stubborn gear-placement swaps. Don't spend the whole budget on
  these.

## How to write a correction

Be specific. Name the defect **and** the desired state, and only a few at a time:

- Good: `"Roderic's shield is on his arm, not leaning on the floor"`,
  `"two figures at the table, not three"`, `"keep Roderic's armor bright
  blue-and-gold — it is muted grey here"`.
- Bad: `"make it better"`, `"fix the composition"`.

Each correction string carries straight into the composer's `--correction` flag.

## Judge adherence, not pixel-match

Generations vary in framing and zoom between runs — that variation is **not** a
defect. Judge style, palette, likeness, and content adherence. A correct image
framed differently from the prior pass is still correct; do not "refine" it just
to match the earlier framing.

## Stopping rule (mandatory)

Cap the refine loop at ~3 passes. At the cap, **accept the best image so far and
set the verdict to `flag`** — never loop indefinitely burning generations on a
defect that will not take.

## Output

Return the result object the scene worker passes back:

```json
{ "image_path": "image-test/<name or name-vN>.jpg",
  "verdict": "accept | refine | flag",
  "notes": "what was judged, what (if anything) was corrected, what remains" }
```

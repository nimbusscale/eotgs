# Illustrate — Architecture & Decomposition

How the campaign-illustration system is structured: what is a skill, what is a
subagent, what is a deterministic script, and where the boundaries go. This is
the design the `illustrate-*` work builds toward. It supersedes the older
`dev/illustrate-session-skill-seed.md` (removed) for anything about
decomposition and orchestration; for the prompt-assembly model and the validated
house-style injection algorithm, see `dev/house-style-injection.md`.

## The organizing principle

Three kinds of thing, kept deliberately separate:

- **A skill is knowledge.** Reusable instructions a model follows. It does not
  own an execution context and does not spawn subagents — that keeps it
  composable, runnable either inline or inside a subagent.
- **A subagent is an execution context.** An isolated conversation with its own
  context window that runs throwaway-heavy work and returns only a conclusion.
  Subagents are introduced by *orchestrators*, at the points where context
  isolation matters — never by the skills themselves.
- **A script is the deterministic floor.** Dumb, reliable, testable. No
  judgment. `compose_image_prompt.py` and `generate_image.py` are this layer.

The judgment lives in the model layer (skills); the reliability lives in the
script layer; the isolation lives in the subagent layer. Most "where should this
go?" questions resolve by asking which of the three a concern belongs to.

**Subagent boundary rule:** put a subagent wherever the work (a) generates a lot
of throwaway context — especially image reads, which are token-heavy — and (b)
you only need the conclusion back. Use only **one level** of nesting from the
main loop; Claude Code limits subagent nesting depth, so do not design for
sub-subagents.

## Components

| Concern | Primitive | Notes |
|---|---|---|
| Pick key moments, build a brief each, collect results | `illustrate-session` — **command**, main context, thin | Mostly reads the session KB + judgment. Stays light **only because it never touches the generated images itself.** |
| Generate ONE good scene to confidence | **subagent**, one per moment | The primary isolation boundary. All candidate/refine image churn lives here and dies with the subagent. |
| How to make a scene (resolve → refs → compose → evaluate → refine) | `illustrate-scene` — **skill** (worker knowledge) | Composable: runs inline when you invoke it manually, or inside a per-scene subagent when batched. Does not spawn its own subagent. |
| "Is this image good? regenerate?" | `references/evaluate.md` — **knowledge**, read inline by the scene worker | The worker already holds the brief, the references, and the result — cheapest to judge there. |
| Mint a new reference plate when one is missing | `generate-reference-plate` — **separate skill + its own subagent**, human-initiated | Produces *durable canon*; different lifecycle from throwaway scene images. Never minted silently mid-scene. |
| Assemble the prompt / call the API | `compose_image_prompt.py`, `generate_image.py` — **scripts** | Already built. The injection algorithm is validated (see house-style-injection.md). |

## Topology

```
/illustrate-session N            COMMAND — main context, thin orchestrator
  • read session summary → pick 3–5 moments → build a brief each
  • PRE-FLIGHT: do all needed references exist? (cheap: check image-map.yaml)
       └─ if any missing → generate-reference-plate (subagent) → human approves
          ...BEFORE the scene batch, so canon is blessed up front
  • for each moment → spawn a SUBAGENT (isolation boundary ↓)
  • collect {path, verdict, notes} ×N → present the set to the human
        │
        └── SUBAGENT: "illustrate one scene to confidence"   (isolated context)
              follows the ILLUSTRATE-SCENE skill:
                1. resolve entities → pick references (image + prompt spec)
                2. write scene-request → run compose_image_prompt.py   (script)
                3. Read the generated image back
                4. evaluate vs brief + reference images  (references/evaluate.md)
                5. defective & fixable? → feed the image back + a correction
                   instruction, regenerate
                   ↳ bounded: max ~3 tries, else accept-best-so-far + flag
                6. return ONLY {final path, verdict, notes}
              ← every candidate and every retry read stays trapped in here
```

## Why the skill does not own the subagent

It is tempting to make `illustrate-scene` spawn its own subagent so a single
call protects context. Don't — flip it: **the subagent uses the skill.**

- If the skill spawned a subagent internally, then `illustrate-session`'s
  per-scene subagent calling the skill would be a subagent spawning a subagent —
  hitting the nesting limit.
- A manual `/illustrate-scene` call would then hide the work from you, when for a
  single image you actually *want* to see the candidates and choose.

So the orchestrator decides when isolation is needed:

- **Manual single use** → runs inline; you are the judge and you see the output.
- **Automated batch** (`illustrate-session`) → wraps each scene in a subagent so
  your main context never accumulates 15 candidate images.

Keeping the skill subagent-agnostic is what lets new callers (future commands,
other tools) compose it freely.

## Data contracts

- **Brief** (orchestrator → scene worker): `description` (required),
  `characters`, `location`, optional `aspect_ratio` / `weapons` / lighting tweak.
  See `.claude/commands/illustrate-scene.md` for the full shape.
- **Scene-request JSON** (worker → composer): the `compose_image_prompt.py`
  input contract — `name`, `type`, `aspect_ratio`, `scene{}`, `references[]`
  (each `role` + `image` + `prompt`), `weapons`. The composer handles all
  house-style injection and palette scoping from this.
- **Result** (scene worker → orchestrator): `{ image_path, verdict, notes }` —
  only the conclusion, not the candidate images. This is what gives the
  orchestrator confidence in what it got back without paying the context cost.

Generated scenes are *candidates* and land under `image-test/` (along with the
composed-prompt scratch); `images/` is reserved for publish-ready assets synced
to the server. Promotion is a deliberate human step — move the file into
`images/` and register it in `config/image-map.yaml`. Neither directory is
committed.

## The evaluator

Good evaluation needs three things in context: the **brief** (what was wanted),
the **reference image(s)** (what the character should look like — this is how you
catch the "shield is on his leg, not strapped to his arm" class of error), and
the **generated image**. The scene worker already holds all three, so inline
evaluation is the cheap default.

Two upgrades to add later without restructuring:

- **Independent critic.** A separate critic subagent gives a less biased verdict
  than the agent that just made the image (a generator tends to like its own
  work). Costs a re-read of the image; worth it for final assets, overkill for
  drafts.
- **Stopping rule (mandatory).** Some defects do not take no matter the wording —
  the spike proved this with Paxton's left/right divine marks, which never
  corrected. Shield-on-arm-vs-leg may be the same class. So: cap refine passes
  (~3), then accept-best-so-far and **flag for a human** rather than looping and
  burning money.

## Missing references

`illustrate-scene` must **not** silently mint a reference plate mid-scene — a
plate defines a character's canonical look indefinitely, so an unvetted
auto-generated one is a landmine. Instead:

- `illustrate-scene` only **detects and reports** a missing reference (a needed
  entity has no `prompt`-linked image in `image-map.yaml`). This is today's
  behavior.
- `illustrate-session` does a **pre-flight check** before the batch: if a chosen
  moment needs an entity with no reference, it runs `generate-reference-plate`
  (its own subagent — plate generation is itself a generate→evaluate→refine
  loop), the **human approves** the plate, it is registered in `image-map.yaml`,
  and *then* the scene batch runs against blessed canon.

This mint-and-approve-then-generate phase separation is far safer than improvising
a reference halfway through scene 3.

## Production concerns (carried forward from the seed)

These were worked out for GPT Image 2 (`gpt-image-2`); fold them into the scripts
and skills as the system matures:

- **Retries:** exponential backoff + jitter; generation can take up to ~2 min for
  complex prompts and rate limits are real.
- **Cost control:** every image input is processed at high fidelity, so a large
  reference costs the same input tokens as a small one — downscale references
  before sending. Edit (reference) calls cost more than plain generations.
- **Consistency ceiling:** character consistency holds on simple compositions and
  degrades as character count / scene complexity grows. Mitigations: fewer
  characters per image, reuse an approved prior scene as a style exemplar on
  drift, stage busy composites (figures first, then environment).
- **Moderation / org verification:** the edits endpoint moderates by default; GPT
  Image models require API org verification on the account.
- **Reproducibility:** generations vary in framing/zoom. Judge style/palette/
  content adherence, not pixel match — for both evaluation and acceptance.

## Current state vs. future

**Built and validated today:**
- `compose_image_prompt.py` — deterministic injection + assembly engine.
- `generate_image.py` — `--prompt-file` (whole-JSON) + repeatable `-i` references
  (switches to the `/v1/images/edits` endpoint).
- `image-map.yaml` — enriched with per-item `description` / `prompt` and a
  `library:` bucket.
- `illustrate-scene` — the single-picture worker, currently authored as a
  `.claude/commands/*.md` file (this repo's convention; surfaced as a skill).
- **evaluate → refine** loop in the scene worker. The worker reads the generated
  image back, judges it against the brief + reference images via
  `.claude/commands/references/evaluate.md`, and on a fixable defect feeds the
  prior image back with a targeted correction, bounded to ~3 passes then
  accept-best-so-far + flag. The composer (`compose_image_prompt.py`) takes
  `--correction` / `--prior` and writes auto-versioned `<name>-vN.jpg` outputs so
  a refine never clobbers the base; `generate_image.py` needed no change.

**Future (this design):**
- `illustrate-session` orchestrator command that picks moments, runs the
  reference pre-flight, and fans out one per-scene subagent per moment.
- `generate-reference-plate` skill for minting + approving new canon plates.
- As `illustrate-scene` / `generate-reference-plate` grow, migrate them to proper
  `SKILL.md` + `references/` layout so progressive disclosure keeps them lean.

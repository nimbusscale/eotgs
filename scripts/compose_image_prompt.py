#!/usr/bin/env python3
"""Compose a single image-generation prompt from a scene request and generate it.

This is the deterministic injection + assembly engine behind the
``illustrate-scene`` skill. It takes a *scene request* JSON (written by the
skill) describing one moment to illustrate — a scene block plus the character /
location reference sub-prompts present — and assembles a single JSON prompt
document by injecting the campaign house style around those sub-prompts, then
hands that document to ``generate_image.py`` together with the reference images.

The injection algorithm (which house-style layers ride, when WORLD_PALETTE is
suppressed, how a strong-palette character is scoped inside a muted scene) is the
one validated by the character-consistency spike; see
``dev/house-style-injection.md`` (§"Injection algorithm").

The generated image and the composed-prompt scratch both land under image-test/
(NOT images/, which is synced to the server). A generated scene is a candidate:
promote it by moving the file into images/ and registering it in image-map.yaml.

Usage:
    OPENAI_ACCESS_KEY=sk-... python3 scripts/compose_image_prompt.py --request req.json
    python3 scripts/compose_image_prompt.py --request req.json --dry-run
    # write a final, publish-ready asset straight to images/ instead of image-test/:
    OPENAI_ACCESS_KEY=sk-... python3 scripts/compose_image_prompt.py --request req.json --out-dir images
    # refine pass — feed the prior generated image back with a targeted fix
    # (writes an auto-versioned image-test/<name>-vN.jpg, leaving the base intact):
    OPENAI_ACCESS_KEY=sk-... python3 scripts/compose_image_prompt.py --request req.json \
        --correction "shield is on his arm, not leaning on the floor" \
        --prior image-test/<name>.jpg

Scene-request JSON (the input contract — see dev/house-style-injection.md):
    {
      "name": "roderic-confronts-voss",
      "type": "scene",                       # "scene" (default) | "plate"
      "aspect_ratio": "16:9 landscape",
      "scene": { "description": "...", "composition": "...",
                 "lighting": "...", "negatives": ["..."] },
      "references": [
        { "role": "character", "name": "Roderic",
          "image": "images/pcs/roderic-pose.jpg",
          "prompt": "config/image/prompts/roderic-reference-plate-prompt.json" },
        { "role": "location", "name": "Aurelion Tunnels",
          "image": "images/aurelion-street-level.jpg",
          "prompt": "config/image/prompts/aurelion-street-level.json" }
      ],
      "weapons": "shown"                     # "shown" (default) | "hidden"
    }
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HOUSE_STYLE_FILE = REPO_ROOT / "config" / "image" / "house-style.json"
# All scratch/test output goes under image-test/ (NOT images/, which is synced
# to the server — only publish-ready assets belong there). The composed prompt
# JSON is scratch, and generated scenes are candidates until a human promotes
# them by moving the file into images/ and adding it to config/image-map.yaml.
SCRATCH_DIR = REPO_ROOT / "image-test"
COMPOSED_DIR = SCRATCH_DIR / ".composed"

# aspect_ratio substrings -> generate_image.py size flag. Checked in order;
# portrait is tested before landscape so "2:3 portrait" never matches "3:2".
SIZE_RULES = [
    (("2:3", "portrait", "vertical"), "--tall"),
    (("16:9", "3:2", "landscape", "wide"), "--wide"),
    (("square", "1:1"), "--square"),
]


def strip_meta(value):
    """Recursively drop authoring-only ``_*`` keys (e.g. _comment, _usage)."""
    if isinstance(value, dict):
        return {
            k: strip_meta(v) for k, v in value.items() if not k.startswith("_")
        }
    if isinstance(value, list):
        return [strip_meta(v) for v in value]
    return value


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"file not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: invalid JSON: {exc}")


def classify_palette(spec: dict) -> str:
    """Classify a reference spec's palette mode from its overrides.

    grounded            -> no palette/lighting override; uses the world palette
    strong              -> has a `palette` override (brighter than the default)
    lighting-exception  -> only a `lighting` override (e.g. Paxton's face-marks)
    """
    overrides = spec.get("house_style_overrides", {})
    if "palette" in overrides:
        return "strong"
    if "lighting" in overrides:
        return "lighting-exception"
    return "grounded"


# Character sub-prompt fields stripped in weapons-hidden mode. Top-level keys
# whose name contains one of these tokens are dropped; nested
# house_style_overrides.signature_items is dropped too.
_WEAPON_KEY_TOKENS = ("signature", "weapon")
# Pose/identity fields are dropped only if their prose names a weapon.
_WEAPON_PROSE_TOKENS = ("sword", "blade", "shield", "weapon", "spear", "axe")


def strip_weapons(spec: dict) -> dict:
    """Remove signature-gear/weapon fields from a character sub-prompt.

    Used for ``weapons: hidden`` (non-combat) scenes. Deterministic and
    conservative: drops keys named after signature gear, drops pose fields whose
    text describes a weapon, and drops ``house_style_overrides.signature_items``.
    Hard no-weapon negatives are added separately in the instructions/scene.
    """
    out = {}
    for key, value in spec.items():
        lowered = key.lower()
        if any(token in lowered for token in _WEAPON_KEY_TOKENS):
            continue
        if key == "house_style_overrides" and isinstance(value, dict):
            value = {k: v for k, v in value.items() if k != "signature_items"}
        if (
            "pose" in lowered
            and isinstance(value, str)
            and any(t in value.lower() for t in _WEAPON_PROSE_TOKENS)
        ):
            continue
        out[key] = value
    return out


def next_version_name(out_dir: Path, name: str) -> str:
    """Return the next versioned output slug for a refine pass.

    The base image is ``<name>.jpg``; refines are ``<name>-vN.jpg`` starting at
    v2. Scans ``out_dir`` for existing ``<name>-v*.jpg`` and returns the next
    free ``<name>-vN`` (so a refine never clobbers the base or an earlier pass).
    """
    versions = []
    for path in out_dir.glob(f"{name}-v*.jpg"):
        suffix = path.stem[len(name) + 2:]  # strip the "<name>-v" prefix
        if suffix.isdigit():
            versions.append(int(suffix))
    return f"{name}-v{max(versions, default=1) + 1}"


def size_flag(aspect_ratio: str) -> str:
    text = (aspect_ratio or "").lower()
    for needles, flag in SIZE_RULES:
        if any(n in text for n in needles):
            return flag
    return "--wide"


def _role_label(role: str) -> str:
    return {
        "character": "the identity reference for",
        "location": "the location reference for",
    }.get(role, "the reference for")


def build_instructions(
    references: list[dict],
    *,
    is_plate: bool,
    world_palette: bool,
    location_strong: bool,
    has_overrides: bool,
    weapons_hidden: bool,
) -> str:
    """Build the natural-language header that carries precedence + scoping.

    This is the text header the spike's tests proved necessary, now carried as a
    JSON field rather than a separate prompt prefix. It enumerates the numbered
    image manifest and states each character's palette status explicitly.
    """
    kind = "character reference plate" if is_plate else "scene"
    lines = [
        f"Render a single campaign illustration (a {kind}). The numbered "
        "reference images below are identity and style sources, NOT a "
        "composition to copy.",
        "",
        "Image manifest:",
    ]
    for i, ref in enumerate(references, start=1):
        lines.append(
            f"- Image {i} is {_role_label(ref['role'])} {ref['name']}."
        )

    lines += [
        "",
        "Apply the HOUSE STYLE block as the global rendering rules (medium, "
        "lighting, material honesty, tone, and global avoids). Then render the "
        "SCENE block (setting, action, composition, mood). Where the scene "
        "gives concrete details, those take precedence over generic "
        "house-style defaults; otherwise the house style governs. Each "
        "reference's sub-prompt governs that subject's identity and canonical "
        "palette.",
        "",
        "Palette scoping:",
    ]

    if location_strong:
        lines.append(
            "- The environment uses the location reference's bright canonical "
            "palette; do NOT mute, tarnish, or desaturate it."
        )
    else:
        lines.append(
            "- The environment and any grounded figures use the muted world "
            "palette (WORLD_PALETTE)."
        )

    for ref in references:
        if ref["role"] != "character":
            continue
        mode = ref["_palette_mode"]
        name = ref["name"]
        if mode == "strong":
            lines.append(
                f"- {name}: keep the bright canonical palette from "
                f"{name}'s reference — do NOT mute or desaturate this figure, "
                "even against a muted background."
            )
        elif mode == "lighting-exception":
            lines.append(
                f"- {name}: rendered in the muted register EXCEPT for the "
                "canonical lighting exception described in the sub-prompt "
                "(keep it subtle, not scene-lighting)."
            )
        else:
            lines.append(
                f"- {name}: rendered in the muted world palette, grounded and "
                "travel-worn."
            )

    if has_overrides:
        lines += [
            "",
            'IMPORTANT — some sub-prompts contain a "house_style_overrides" '
            "block. Those overrides REPLACE the corresponding house-style "
            "defaults for that subject only (an override palette replaces the "
            "muted default entirely; an override lighting replaces the default "
            "lighting). The medium, tone, material honesty, and global avoids "
            "from the house style still apply to everything.",
        ]

    if weapons_hidden:
        lines += [
            "",
            "WEAPONS HIDDEN — this is a non-combat scene. Do NOT show any "
            "weapons, shields, drawn or sheathed blades, or signature arms "
            "anywhere in the image. Hands rest on props, the table, or at "
            "sides. Ignore any weapon or signature-gear description that may "
            "remain in a sub-prompt.",
        ]

    return "\n".join(lines)


NO_WEAPON_NEGATIVES = [
    "no weapons of any kind",
    "no swords, blades, daggers, or polearms",
    "no shields",
    "no sheathed or holstered signature arms",
]


def compose(request: dict) -> dict:
    """Assemble the single composed prompt document from a scene request."""
    house = load_json(HOUSE_STYLE_FILE)
    gm = strip_meta(house["GLOBAL_MEDIUM"])

    is_plate = request.get("type", "scene") == "plate"
    scene = request.get("scene", {})
    scene_supplies_lighting = bool(scene.get("lighting"))
    weapons_hidden = request.get("weapons", "shown") == "hidden"

    # Load + classify every reference.
    references = []
    has_overrides = False
    for ref in request.get("references", []):
        spec = strip_meta(load_json((REPO_ROOT / ref["prompt"])))
        mode = classify_palette(spec)
        if mode != "grounded":
            has_overrides = True
        if weapons_hidden and ref.get("role") == "character":
            spec = strip_weapons(spec)
        references.append({**ref, "_spec": spec, "_palette_mode": mode})

    # Environment palette decision (house-style-injection.md rule 4 + exception).
    location_modes = [
        r["_palette_mode"] for r in references if r.get("role") == "location"
    ]
    location_strong = bool(location_modes) and all(
        m == "strong" for m in location_modes
    )
    any_grounded_char = any(
        r.get("role") == "character" and r["_palette_mode"] == "grounded"
        for r in references
    )
    # Suppress the world palette only when the whole image is a strong-palette
    # subject (a strong location with no grounded figure needing the muted base).
    world_palette = (not location_strong) or any_grounded_char

    # Always-on GLOBAL_MEDIUM base.
    global_medium = {
        "medium": gm["medium"],
        "tone": gm["tone"],
        "signature_items": gm["signature_items"],
        "avoid_global": gm["avoid_global"],
    }
    if is_plate:
        global_medium["format_for_plates"] = gm["format_for_plates"]
        if not scene_supplies_lighting:
            global_medium["lighting_for_plates"] = gm["lighting_for_plates"]
    else:
        if not scene_supplies_lighting:
            global_medium["lighting_for_scenes"] = gm["lighting_for_scenes"]

    house_style = {"GLOBAL_MEDIUM": global_medium}
    if world_palette:
        house_style["WORLD_PALETTE"] = strip_meta(house["WORLD_PALETTE"])

    instructions = build_instructions(
        references,
        is_plate=is_plate,
        world_palette=world_palette,
        location_strong=location_strong,
        has_overrides=has_overrides,
        weapons_hidden=weapons_hidden,
    )

    # Scene block: append hard no-weapon negatives in weapons-hidden mode.
    scene_block = dict(scene)
    if weapons_hidden:
        negatives = list(scene_block.get("negatives", []))
        for neg in NO_WEAPON_NEGATIVES:
            if neg not in negatives:
                negatives.append(neg)
        scene_block["negatives"] = negatives

    composed_refs = [
        {
            "image": i,
            "role": ref.get("role"),
            "label": ref["name"],
            "spec": ref["_spec"],
        }
        for i, ref in enumerate(references, start=1)
    ]

    return {
        "instructions": instructions,
        "house_style": house_style,
        "references": composed_refs,
        "scene": scene_block,
    }


def main(argv=None) -> str:
    argv = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--request", required=True, help="path to a scene-request JSON"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "assemble + write the composed JSON and print the generate_image "
            "command, but do NOT call the API"
        ),
    )
    parser.add_argument(
        "--out-dir",
        default=str(SCRATCH_DIR),
        help=(
            "directory for the generated image (default: image-test/, treated "
            "as scratch). Pass images/ only for a final, publish-ready asset. "
            "On a refine pass, --correction/--prior feed the prior generated "
            "image back with a targeted fix and write an auto-versioned -vN.jpg"
        ),
    )
    parser.add_argument(
        "--correction",
        action="append",
        metavar="TEXT",
        help=(
            "specific defect from the previous attempt to fix (repeatable). "
            "Injected as a highest-priority directive at the top of the prompt"
        ),
    )
    parser.add_argument(
        "--prior",
        action="append",
        metavar="PATH",
        help=(
            "prior generated image to feed back as an extra likeness reference "
            "(repeatable). Appended after the canonical references"
        ),
    )
    args = parser.parse_args(argv)

    request = load_json(Path(args.request).resolve())
    name = request.get("name")
    if not name:
        raise SystemExit("scene request must have a 'name'")

    composed = compose(request)

    # Refine pass: prepend the correction as the first thing the model reads, so
    # the targeted fix outranks the rest of the (otherwise unchanged) prompt.
    if args.correction:
        directive = "\n".join(
            [
                "CORRECTION (highest priority — the previous attempt had these "
                "specific defects; fix them while keeping everything else):",
                *(f"- {c}" for c in args.correction),
            ]
        )
        composed["instructions"] = directive + "\n\n" + composed["instructions"]

    # Reference images, in manifest order, matching references[].image 1..N.
    images = []
    for ref in request.get("references", []):
        path = REPO_ROOT / ref["image"]
        if not path.is_file():
            raise SystemExit(f"reference image not found: {path}")
        images.append(str(path))

    # Refine pass: append each prior generated image as an extra likeness
    # reference, AFTER the canonical references so they stay primary.
    for prior in args.prior or []:
        path = REPO_ROOT / prior
        if not path.is_file():
            raise SystemExit(f"prior image not found: {path}")
        images.append(str(path))

    # On a refine pass write an auto-versioned slug so the base is never
    # clobbered; the composed JSON is named to match for traceability.
    out_dir_path = REPO_ROOT / args.out_dir
    out_name = name
    if args.correction or args.prior:
        out_name = next_version_name(out_dir_path, name)

    COMPOSED_DIR.mkdir(parents=True, exist_ok=True)
    composed_path = COMPOSED_DIR / f"{out_name}.json"
    composed_path.write_text(
        json.dumps(composed, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    flag = size_flag(request.get("aspect_ratio", ""))
    gen_argv = ["--prompt-file", str(composed_path)]
    for img in images:
        gen_argv += ["-i", img]
    gen_argv += [flag, "--name", out_name, "--out-dir", args.out_dir]

    if args.dry_run:
        print(f"Composed prompt written to {composed_path}")
        printable = " ".join(
            x if x.startswith("-") or x == flag else f'"{x}"' for x in gen_argv
        )
        print(f"Would run: python3 scripts/generate_image.py {printable}")
        return str(composed_path)

    # Prefer calling generate_image.main(argv=...) over a subprocess; both
    # scripts share scripts/ on sys.path when run as scripts/<name>.py.
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    import generate_image

    out_path = generate_image.main(gen_argv)
    print(f"Generated image: {out_path}")
    return out_path


if __name__ == "__main__":
    main()

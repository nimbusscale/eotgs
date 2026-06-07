#!/usr/bin/env python3
"""Generate the derived config maps from per-entity KB frontmatter.

Each ``kb/**/*.md`` file carries a ``---`` YAML frontmatter block that is the
single source of truth for that entity's identity, aliases, hierarchy, and
image associations. This script walks the KB, reads those blocks, and emits
three *generated, committed* artifacts:

1. ``config/entity-aliases.yaml`` — ``name``/``aliases`` (and every
   ``contains[]`` child's name/aliases) folded to the owning entity's ``id``.
   Reuses ``sync_kb_aliases.render_aliases`` so the double-quoted key style and
   category order are identical to the legacy file.
2. ``config/image-map.yaml``     — ``<subdir>/<id>`` (sessions:
   ``sessions/<arc>/<id>``) → ``hero``/``gallery``/``library`` image blocks.
3. ``config/subject-index.yaml`` — ``slug -> [image files]`` built from every
   image's ``subjects:`` list, so the illustrate skills can find every picture
   of an entity (including page-less sub-entities) without an inline dual-scan.

``--check`` regenerates into memory and diffs against the committed files,
exiting non-zero with a unified diff (the integrity gate; clean on ``main``).
``--backfill`` synthesises frontmatter for any file that lacks it, from the
committed alias reverse-map + image-map + the file's bold lore lines.

Follows repo conventions: ``REPO_ROOT``, ``main(argv=None)``, returns the
primary output path, PyYAML only.
"""

import argparse
import difflib
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sync_kb_aliases import render_aliases, CATEGORY_ORDER
from build_manifest import scan_kb_sub_entities

REPO_ROOT = Path(__file__).resolve().parent.parent
KB_ROOT = REPO_ROOT / "kb"
ENTITY_ALIASES_PATH = REPO_ROOT / "config" / "entity-aliases.yaml"
IMAGE_MAP_PATH = REPO_ROOT / "config" / "image-map.yaml"
SUBJECT_INDEX_PATH = REPO_ROOT / "config" / "subject-index.yaml"

# Map KB subdirectory -> entity-aliases.yaml category. Extends the legacy
# sync_kb_aliases.SUBDIR_TO_CATEGORY with pcs (PCs live under `characters:`).
SUBDIR_TO_CATEGORY = {
    "pcs": "characters",
    "npcs": "characters",
    "locations": "locations",
    "items": "items",
    "factions": "factions",
    "world": "world",
}

# Map KB subdirectory -> frontmatter `type` value used during backfill.
SUBDIR_TO_TYPE = {
    "pcs": "pc",
    "npcs": "npc",
    "locations": "location",
    "items": "item",
    "factions": "faction",
    "world": "world",
    "sessions": "session",
    "story-arcs": "story-arc",
}

# H1 titles that carry a leading article the canonical alias drops (or differ
# in spelling). Backfill sets `name` to the bare alias form so the generated
# name->id pair matches an alias already present in entity-aliases.yaml and the
# regeneration introduces no new keys.
NAME_OVERRIDES = {
    "ashbrook": "Ashbrook",
    "ashen-flow": "Ashen Flow",
    "bonewall": "Bonewall",
    "cinderwall": "Cinderwall",
    "cragmarr": "Cragmarr",
    "greenholt-bloodline": "Greenholt Bloodline",
    "middle-kingdoms": "Middle Kingdoms",
    "old-gods-and-new-gods": "Old Gods and New Gods",
}

# Header comment block reused verbatim as the "DO NOT EDIT" preamble of the
# generated image-map.yaml (kept in sync with the documented schema).
IMAGE_MAP_HEADER = """\
# GENERATED FILE — DO NOT EDIT BY HAND.
# Regenerate with: python3 scripts/build_index.py
# Source of truth is the `images:` block in each kb/**/*.md frontmatter.
#
# Maps KB entity (subdir/slug) -> images.
# Image files live in images/ (repo root, gitignored). Copied into the site
# at build time by scripts/build_site.py.
#
# `hero`: rendered at the top of the page with no caption. `gallery`: list
#   rendered in a "## Gallery" section, each with its caption. `library`:
#   reference-only images (studio plates) that are NEVER published — their
#   `file:` is a REPO-ROOT-RELATIVE path (config/image/library/...), unlike
#   hero/gallery files which live under images/.
#
# Per image item: file (required), caption, alt, description, prompt (path to
#   its spec JSON), subjects (list of entity slugs depicted — drives the
#   cross-map reference index in config/subject-index.yaml).
"""

SUBJECT_INDEX_HEADER = """\
# GENERATED FILE — DO NOT EDIT BY HAND.
# Regenerate with: python3 scripts/build_index.py
# Maps entity slug -> list of image files that depict it (from every image's
# `subjects:` list across all kb frontmatter). Lets the illustrate skills find
# every picture of a slug — including page-less sub-entities — at a glance.
"""

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?", re.DOTALL)
_TITLE_RE = re.compile(r"^# (.+)", re.MULTILINE)
_STATUS_RE = re.compile(r"^\*\*Status:\*\*\s*(.+)$", re.MULTILINE)
_DATE_PLAYED_RE = re.compile(r"\*\*Date Played:\*\*\s*(\d{4}-\d{2}-\d{2})")


def split_frontmatter(text):
    """Split a leading ``---`` YAML block off markdown text.

    Returns ``(frontmatter_dict_or_None, body)``. If the file has no
    frontmatter, returns ``(None, text)`` unchanged.
    """
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return None, text
    data = yaml.safe_load(m.group(1)) or {}
    if not isinstance(data, dict):
        return None, text
    return data, text[m.end():]


def extract_title(text):
    """Return the text after the first ``# `` header, or None."""
    m = _TITLE_RE.search(text)
    return m.group(1).strip() if m else None


def slugify_name(name):
    """Filename slug: lowercase, hyphens, drop leading article, no punctuation."""
    s = name.lower().strip()
    s = re.sub(r"^(the|a|an)\s+", "", s)
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"\s+", "-", s)
    return s


def load_entities():
    """Walk the KB, returning one record per markdown file.

    Each record: ``{path, rel, subdir, parent_dir, stem, fm, body}`` where
    ``fm`` is the parsed frontmatter dict (or None) and ``body`` is the text
    after the frontmatter (or the whole file when there is none).
    """
    entities = []
    for md_file in sorted(KB_ROOT.rglob("*.md")):
        if md_file.name == ".gitkeep":
            continue
        rel = md_file.relative_to(KB_ROOT)
        parts = rel.parts
        text = md_file.read_text(encoding="utf-8")
        fm, body = split_frontmatter(text)
        entities.append({
            "path": md_file,
            "rel": rel,
            "subdir": parts[0],
            "parent_dir": parts[-2] if len(parts) > 1 else None,
            "stem": md_file.stem,
            "fm": fm,
            "body": body,
        })
    return entities


def load_committed_reverse_aliases():
    """Read the committed entity-aliases.yaml as {slug: [alias, ...]} (in order)."""
    if not ENTITY_ALIASES_PATH.exists():
        return {}
    data = yaml.safe_load(ENTITY_ALIASES_PATH.read_text(encoding="utf-8")) or {}
    reverse = {}
    for category in data.values():
        if not isinstance(category, dict):
            continue
        for alias, slug in category.items():
            reverse.setdefault(slug, [])
            if alias not in reverse[slug]:
                reverse[slug].append(alias)
    return reverse


def load_committed_image_map():
    """Read the committed image-map.yaml as {key: {hero?, gallery?, library?}}."""
    if not IMAGE_MAP_PATH.exists():
        return {}
    data = yaml.safe_load(IMAGE_MAP_PATH.read_text(encoding="utf-8")) or {}
    return {k: v for k, v in data.items() if isinstance(v, dict)}


def entity_name(e):
    """Resolved display name for an entity: frontmatter `name` or its H1."""
    fm = e["fm"] or {}
    return fm.get("name") or extract_title(e["body"]) or e["stem"]


def entity_id(e):
    """Resolved stable id: frontmatter `id` or the filename slug."""
    fm = e["fm"] or {}
    return fm.get("id", e["stem"])


def image_map_key(e):
    """Reconstruct the image-map key for an entity.

    Sessions key on ``sessions/<arc>/<id>`` (arc = the file's parent dir);
    everything else on ``<subdir>/<id>``.
    """
    eid = entity_id(e)
    if e["subdir"] == "sessions" and e["parent_dir"]:
        return f"sessions/{e['parent_dir']}/{eid}"
    return f"{e['subdir']}/{eid}"


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

def build_alias_data(entities):
    """Build {category: {alias: id}} from frontmatter (with a header-scan fallback).

    Files WITH frontmatter contribute ``name``/``aliases`` and each
    ``contains[]`` child's name/aliases, all folded to the entity ``id``.
    Files WITHOUT frontmatter fall back to the committed aliases for their slug
    plus any ``## [[Name]]`` sub-entity headers, so nothing is lost mid-backfill.
    """
    data = {cat: {} for cat in CATEGORY_ORDER}
    committed_reverse = load_committed_reverse_aliases()
    sub_entity_map, _ = scan_kb_sub_entities()

    for e in entities:
        category = SUBDIR_TO_CATEGORY.get(e["subdir"])
        if not category:
            continue
        bucket = data[category]
        fm = e["fm"]
        if fm is not None:
            eid = entity_id(e)
            bucket[entity_name(e)] = eid
            for alias in fm.get("aliases") or []:
                bucket[alias] = eid
            for child in fm.get("contains") or []:
                bucket[child["name"]] = eid
                for alias in child.get("aliases") or []:
                    bucket[alias] = eid
        else:
            # Fallback for un-migrated files.
            slug = e["stem"]
            bucket[entity_name(e)] = slug
            for alias in committed_reverse.get(slug, []):
                bucket[alias] = slug

    # Header-scan fallback only covers slugs whose file has no frontmatter yet.
    fm_slugs = {entity_id(e) for e in entities if e["fm"] is not None}
    for name, info in sub_entity_map.items():
        category = SUBDIR_TO_CATEGORY.get(info["category"])
        if not category:
            continue
        slug = info["parent_file"].split("/")[-1].replace(".md", "")
        if slug in fm_slugs:
            continue  # frontmatter is authoritative for migrated files
        data[category].setdefault(name, slug)

    return {cat: entries for cat, entries in data.items() if entries}


def build_image_map(entities):
    """Build {key: {hero?, gallery?, library?}} from frontmatter `images` blocks."""
    image_map = {}
    for e in entities:
        fm = e["fm"]
        if not fm:
            continue
        images = fm.get("images")
        if not images:
            continue
        block = {}
        for kind in ("hero", "gallery", "library"):
            if images.get(kind):
                block[kind] = images[kind]
        if block:
            image_map[image_map_key(e)] = block
    return image_map


def build_subject_index(entities):
    """Build {slug: [image files]} from every image's `subjects` list."""
    index = {}
    for e in entities:
        fm = e["fm"]
        if not fm:
            continue
        images = fm.get("images")
        if not images:
            continue
        items = []
        if images.get("hero"):
            items.append(images["hero"])
        items.extend(images.get("gallery") or [])
        items.extend(images.get("library") or [])
        for item in items:
            for slug in item.get("subjects") or []:
                index.setdefault(slug, [])
                if item["file"] not in index[slug]:
                    index[slug].append(item["file"])
    return {slug: index[slug] for slug in sorted(index)}


def render_image_map(image_map):
    body = yaml.dump(image_map, sort_keys=False, allow_unicode=True, default_flow_style=False)
    return IMAGE_MAP_HEADER + "\n" + body


def render_subject_index(subject_index):
    if subject_index:
        body = yaml.dump(subject_index, sort_keys=False, allow_unicode=True, default_flow_style=False)
    else:
        body = "{}\n"
    return SUBJECT_INDEX_HEADER + "\n" + body


def generate(entities):
    """Return {path: rendered_text} for the three generated artifacts."""
    return {
        ENTITY_ALIASES_PATH: render_aliases(build_alias_data(entities)),
        IMAGE_MAP_PATH: render_image_map(build_image_map(entities)),
        SUBJECT_INDEX_PATH: render_subject_index(build_subject_index(entities)),
    }


def check(outputs):
    """Diff generated text against committed files. Returns list of diff strings."""
    diffs = []
    for path, new_text in outputs.items():
        old_text = path.read_text(encoding="utf-8") if path.exists() else ""
        if old_text != new_text:
            rel = path.relative_to(REPO_ROOT)
            diff = difflib.unified_diff(
                old_text.splitlines(keepends=True),
                new_text.splitlines(keepends=True),
                fromfile=f"committed/{rel}",
                tofile=f"generated/{rel}",
            )
            diffs.append("".join(diff))
    return diffs


# ---------------------------------------------------------------------------
# Backfill
# ---------------------------------------------------------------------------

def synth_frontmatter(e, reverse_aliases, image_map):
    """Synthesise a frontmatter dict for a file that has none."""
    stem = e["stem"]
    body = e["body"]
    fm = {}

    # id: arc index pages key on their arc dir (stem "index" isn't unique).
    if e["subdir"] in ("sessions", "story-arcs") and stem == "index":
        fm["id"] = e["parent_dir"]
    else:
        fm["id"] = stem

    # type
    if stem == "index" and e["subdir"] == "sessions":
        fm["type"] = "arc"
    else:
        fm["type"] = SUBDIR_TO_TYPE.get(e["subdir"], e["subdir"])

    # name
    name = NAME_OVERRIDES.get(stem) or extract_title(body) or stem
    fm["name"] = name

    # status (PCs)
    if e["subdir"] == "pcs":
        m = _STATUS_RE.search(body)
        if m:
            fm["status"] = m.group(1).strip()

    # arc + date (sessions)
    if e["subdir"] == "sessions" and stem != "index":
        fm["arc"] = e["parent_dir"]
        m = _DATE_PLAYED_RE.search(body)
        if m:
            fm["date"] = m.group(1)

    # aliases (alias-generating subdirs only), from the committed reverse map,
    # with the canonical name removed (it is emitted via `name`).
    if SUBDIR_TO_CATEGORY.get(e["subdir"]):
        aliases = [a for a in reverse_aliases.get(stem, []) if a != name]
        if aliases:
            fm["aliases"] = aliases

    # images, copied verbatim from the committed image-map entry.
    key = image_map_key(e)
    if key in image_map:
        block = {}
        for kind in ("hero", "gallery", "library"):
            if image_map[key].get(kind):
                block[kind] = image_map[key][kind]
        if block:
            fm["images"] = block

    return fm


def render_frontmatter(fm):
    text = yaml.dump(fm, sort_keys=False, allow_unicode=True, default_flow_style=False)
    return f"---\n{text}---\n"


def backfill(entities):
    """Prepend synthesised frontmatter to every file that lacks it. Returns count."""
    reverse_aliases = load_committed_reverse_aliases()
    image_map = load_committed_image_map()
    written = 0
    for e in entities:
        if e["fm"] is not None:
            continue
        fm = synth_frontmatter(e, reverse_aliases, image_map)
        original = e["path"].read_text(encoding="utf-8")
        e["path"].write_text(render_frontmatter(fm) + original, encoding="utf-8")
        written += 1
    return written


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate config maps from per-entity KB frontmatter.",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--check", action="store_true",
        help="Diff generated output against committed files; exit non-zero if they differ.",
    )
    group.add_argument(
        "--backfill", action="store_true",
        help="Synthesise frontmatter for files that lack it (one-time migration).",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    if args.backfill:
        entities = load_entities()
        n = backfill(entities)
        print(f"Backfilled frontmatter into {n} file(s).")
        return str(ENTITY_ALIASES_PATH)

    entities = load_entities()
    outputs = generate(entities)

    if args.check:
        diffs = check(outputs)
        if diffs:
            print("build_index --check FAILED: generated output differs from committed files.\n")
            for d in diffs:
                print(d)
            sys.exit(1)
        print("build_index --check OK: generated output matches committed files.")
        return str(ENTITY_ALIASES_PATH)

    for path, text in outputs.items():
        path.write_text(text, encoding="utf-8")
        print(f"Wrote {path.relative_to(REPO_ROOT)}")
    return str(ENTITY_ALIASES_PATH)


if __name__ == "__main__":
    main()

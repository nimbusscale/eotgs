#!/usr/bin/env python3
"""Mirror the campaign KB into a Foundry VTT JournalEntry compendium.

Reads the same per-entity frontmatter + body that drive the website and the
Claude-Project exports, and regenerates the ``grimwild-kb`` Foundry module:

- ``compendium/grimwild-kb/src/kb/*.json`` — one JSON file per Folder and per
  JournalEntry (the diffable source of truth, committed). Each JournalEntry
  embeds its pages as full objects; the Foundry CLI expands them into separate
  ``!journal.pages!`` documents at pack time.
- ``compendium/grimwild-kb/packs/kb/``      — the compiled LevelDB (gitignored).
- ``compendium/grimwild-kb/assets/``        — hero+gallery images copied from
  ``images/`` (gitignored).

Scope mirrors the site: NPCs, Locations, Factions, Items, World, PCs, and
Sessions (with arc sub-folders). ``story-arcs/`` and ``gm-notes/`` are excluded.

Everything is GM-only by default (``ownership.default: 0``); the GM shares art
per-image via Foundry's right-click "Show to Players". Document ``_id``s are
derived deterministically from stable keys so cross-entry ``@UUID`` links
survive every rebuild, and ``createdTime``/``modifiedTime`` are pinned to ``0``
so re-running the build produces a churn-free diff.

Follows repo conventions: ``REPO_ROOT``, ``main(argv=None)`` returning the
primary output path, PyYAML + regex only (no new pip dependency — the
markdown→HTML conversion is purpose-built).
"""

import argparse
import hashlib
import html
import re
import shutil
import string
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_index import (
    load_entities,
    entity_id,
    entity_name,
    slugify_name,
)
from build_site import _WIKILINK_RE, _entity_images

REPO_ROOT = Path(__file__).resolve().parent.parent
MODULE_DIR = REPO_ROOT / "compendium" / "grimwild-kb"
SRC_DIR = MODULE_DIR / "src" / "kb"
PACKS_DIR = MODULE_DIR / "packs"
ASSETS_DIR = MODULE_DIR / "assets"
IMAGE_SRC_DIR = REPO_ROOT / "images"
ALIASES_FILE = REPO_ROOT / "config" / "entity-aliases.yaml"

MODULE_ID = "grimwild-kb"
PACK_NAME = "kb"
ASSET_URL_PREFIX = f"modules/{MODULE_ID}/assets"

# In-scope subdirs and their Foundry folder labels, in display order.
TYPE_FOLDERS = [
    ("npcs", "NPCs"),
    ("locations", "Locations"),
    ("factions", "Factions"),
    ("items", "Items"),
    ("world", "World"),
    ("pcs", "PCs"),
    ("sessions", "Sessions"),
]
IN_SCOPE = {subdir for subdir, _ in TYPE_FOLDERS}

# Constant _stats block — pinned coreVersion/systemId mirror the live grimwild
# world's exports; times are 0 so rebuilds don't churn the committed JSON.
STATS = {
    "compendiumSource": None,
    "duplicateSource": None,
    "exportSource": None,
    "coreVersion": "13.351",
    "systemId": "grimwild",
    "systemVersion": "0.3.1",
    "createdTime": 0,
    "modifiedTime": 0,
    "lastModifiedBy": None,
}

_B62 = string.ascii_uppercase + string.ascii_lowercase + string.digits  # 62 chars


def stable_id(key):
    """Deterministic 16-char [A-Za-z0-9] Foundry id from an arbitrary key.

    sha1(key) → big int → base62 → first 16 chars, deterministically padded so
    the same key always yields the same id (cross-entry links stay valid across
    rebuilds).
    """
    n = int.from_bytes(hashlib.sha1(key.encode()).digest(), "big")
    out = []
    while n and len(out) < 16:
        n, r = divmod(n, 62)
        out.append(_B62[r])
    return ("".join(out) + "A" * 16)[:16]


# ---------------------------------------------------------------------------
# Markdown → HTML (purpose-built; handles the subset the KB actually uses:
# h2/h3, unordered lists, blockquotes, GFM pipe tables, bold/italic, and
# one-sentence-per-line paragraphs preserved with <br>).
# ---------------------------------------------------------------------------

_ENRICHER_RE = re.compile(r"@UUID\[[^\]]+\]\{[^}]*\}")
_HEADING_RE = re.compile(r"^(#{2,3})\s+(.*)$")
_LIST_RE = re.compile(r"^\s*[-*]\s+(.*)$")
_TABLE_SEP_RE = re.compile(r"^\s*\|?[\s:|-]*-[\s:|-]*\|?\s*$")


def _inline(text):
    """Escape text and apply bold/italic, preserving @UUID enrichers verbatim."""
    tokens = []

    def _stash(m):
        tokens.append(m.group(0))
        return f"\x00{len(tokens) - 1}\x00"

    text = _ENRICHER_RE.sub(_stash, text)
    text = html.escape(text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", text)
    text = re.sub(r"\x00(\d+)\x00", lambda m: tokens[int(m.group(1))], text)
    return text


def _table_cells(row):
    return [c.strip() for c in row.strip().strip("|").split("|")]


def _render_table(rows):
    header = _table_cells(rows[0])
    out = ["<table><thead><tr>"]
    out += [f"<th>{_inline(c)}</th>" for c in header]
    out.append("</tr></thead><tbody>")
    for row in rows[2:]:
        cells = _table_cells(row)
        out.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in cells) + "</tr>")
    out.append("</tbody></table>")
    return "".join(out)


def md_to_html(md):
    """Convert wikilink-resolved, H1-stripped markdown body to Foundry HTML."""
    lines = md.split("\n")
    n = len(lines)
    parts = []
    para = []
    i = 0

    def flush_para():
        if para:
            parts.append("<p>" + "<br>".join(_inline(l) for l in para) + "</p>")
            para.clear()

    while i < n:
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            flush_para()
            i += 1
            continue

        m = _HEADING_RE.match(line)
        if m:
            flush_para()
            level = len(m.group(1))
            parts.append(f"<h{level}>{_inline(m.group(2).strip())}</h{level}>")
            i += 1
            continue

        # GFM pipe table: a "| ... |" row immediately followed by a separator row.
        if stripped.startswith("|") and i + 1 < n and _TABLE_SEP_RE.match(lines[i + 1]):
            flush_para()
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                rows.append(lines[i])
                i += 1
            parts.append(_render_table(rows))
            continue

        if stripped.startswith(">"):
            flush_para()
            quote = []
            while i < n and lines[i].strip().startswith(">"):
                quote.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            parts.append(
                "<blockquote>" + "<br>".join(_inline(q) for q in quote) + "</blockquote>"
            )
            continue

        m = _LIST_RE.match(line)
        if m:
            flush_para()
            items = []
            while i < n and _LIST_RE.match(lines[i]):
                items.append(_LIST_RE.match(lines[i]).group(1).strip())
                i += 1
            parts.append("<ul>" + "".join(f"<li>{_inline(it)}</li>" for it in items) + "</ul>")
            continue

        para.append(stripped)
        i += 1

    flush_para()
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Wikilinks → Foundry @UUID enrichers
# ---------------------------------------------------------------------------

def load_alias_map():
    """Read entity-aliases.yaml as a flat {alias: slug} forward map."""
    alias_map = {}
    if not ALIASES_FILE.exists():
        return alias_map
    data = yaml.safe_load(ALIASES_FILE.read_text(encoding="utf-8")) or {}
    for category in data.values():
        if isinstance(category, dict):
            alias_map.update(category)
    return alias_map


def _resolve_slug(target, alias_map, id_map):
    """Resolve a wikilink target to an in-scope entity slug, or None."""
    if target in alias_map and alias_map[target] in id_map:
        return alias_map[target]
    s = slugify_name(target)
    if s in id_map:
        return s
    tl = target.lower()
    for alias, slug in alias_map.items():
        if alias.lower() == tl and slug in id_map:
            return slug
    return None


def resolve_wikilinks(text, alias_map, id_map):
    """Rewrite ``[[Target|Display]]`` to a pack-relative @UUID enricher.

    Anchors are dropped to the parent entry (sub-entities already fold to their
    parent slug via entity-aliases.yaml). Unresolved links fall back to the
    plain display text, exactly like the site.
    """

    def _replace(m):
        raw_target = m.group(1).strip()
        alias = m.group(2)

        if "#" in raw_target:
            target = raw_target.split("#", 1)[0].strip()
        else:
            target = raw_target
        display = alias.strip() if alias else target

        slug = _resolve_slug(target, alias_map, id_map)
        if slug is None:
            return display  # plain text (escaped downstream by _inline)
        uuid = f"Compendium.{MODULE_ID}.{PACK_NAME}.JournalEntry.{id_map[slug]}"
        return f"@UUID[{uuid}]{{{display}}}"

    return _WIKILINK_RE.sub(_replace, text)


def strip_h1(body):
    """Remove the first ``# `` heading line."""
    return re.sub(r"^# .+\n?", "", body, count=1)


# ---------------------------------------------------------------------------
# Document builders
# ---------------------------------------------------------------------------

def _asset_src(file):
    """URL for an image referenced in a page (URL-encoded, asset-relative)."""
    from urllib.parse import quote
    return f"{ASSET_URL_PREFIX}/{quote(file)}"


def make_folder(name, fid, sort, parent=None):
    return {
        "name": name,
        "_id": fid,
        "type": "JournalEntry",
        "sorting": "a",
        "sort": sort,
        "folder": parent,
        "color": None,
        "flags": {},
        "_stats": dict(STATS),
        "_key": f"!folders!{fid}",
    }


def _image_page(journal_id, page_key, name, src, caption, sort, show_title):
    pid = stable_id(page_key)
    return {
        "name": name,
        "type": "image",
        "_id": pid,
        "title": {"show": show_title, "level": 1},
        "image": {"caption": caption},
        "text": {"format": 1},
        "video": {"controls": True, "volume": 0.5},
        "src": src,
        "system": {},
        "category": None,
        "sort": sort,
        "ownership": {"default": -1},
        "flags": {},
        "_stats": dict(STATS),
        "_key": f"!journal.pages!{journal_id}.{pid}",
    }


def _text_page(journal_id, page_key, name, content, sort):
    pid = stable_id(page_key)
    return {
        "name": name,
        "type": "text",
        "_id": pid,
        "title": {"show": True, "level": 1},
        "image": {},
        "text": {"format": 1, "content": content, "markdown": ""},
        "video": {"controls": True, "volume": 0.5},
        "src": None,
        "system": {},
        "category": None,
        "sort": sort,
        "ownership": {"default": -1},
        "flags": {},
        "_stats": dict(STATS),
        "_key": f"!journal.pages!{journal_id}.{pid}",
    }


def build_journal(e, slug, folder_id, sort, alias_map, id_map, referenced):
    """Build one JournalEntry doc (with embedded pages) for an entity."""
    jid = id_map[slug]
    name = entity_name(e)
    fm = e["fm"] or {}
    images = fm.get("images") or {}
    hero = images.get("hero")
    gallery = images.get("gallery") or []

    pages = []

    # Hero image page (lead art; title hidden, the journal name already labels it).
    hero_src = None
    if hero:
        referenced.add(hero["file"])
        hero_src = _asset_src(hero["file"])
        caption = hero.get("caption") or hero.get("alt") or ""
        pages.append(
            _image_page(jid, f"page:{slug}:hero", name, hero_src, caption, 0, show_title=False)
        )

    # Text page (the prose body, wikilinks resolved to @UUID enrichers).
    body = strip_h1(e["body"])
    body = resolve_wikilinks(body, alias_map, id_map)
    content = md_to_html(body)
    pages.append(_text_page(jid, f"page:{slug}:text", name, content, 100000))

    # Gallery image pages (each shareable via "Show to Players").
    for k, img in enumerate(gallery):
        referenced.add(img["file"])
        caption = img.get("caption", "")
        page_name = caption if caption else f"Image {k + 1}"
        pages.append(
            _image_page(
                jid,
                f"page:{slug}:gallery:{img['file']}",
                page_name,
                _asset_src(img["file"]),
                caption,
                200000 + k * 100000,
                show_title=True,
            )
        )

    return {
        "name": name,
        "_id": jid,
        "img": hero_src,
        "pages": pages,
        "folder": folder_id,
        "categories": [],
        "sort": sort,
        "ownership": {"default": 0},
        "flags": {MODULE_ID: {"kbId": slug, "kbType": fm.get("type") or e["subdir"]}},
        "_stats": dict(STATS),
        "_key": f"!journal!{jid}",
    }


# ---------------------------------------------------------------------------
# Packing
# ---------------------------------------------------------------------------

def _pack_commands():
    """Candidate fvtt invocations, in priority order (installed binary first)."""
    cmds = []
    found = shutil.which("fvtt")
    if found:
        cmds.append([found])
    vendored = MODULE_DIR / "node_modules" / ".bin" / "fvtt"
    if vendored.exists():
        cmds.append([str(vendored)])
    # Last resort: npx (needs network to resolve the package the first time).
    cmds.append(["npx", "--yes", "@foundryvtt/foundryvtt-cli", "fvtt"])
    return cmds


def pack_leveldb():
    """Compile src/kb JSON into packs/kb LevelDB via the Foundry CLI.

    The CLI appends the pack name to ``--out``, so ``--out`` points at the
    ``packs`` parent (yields ``packs/kb``, not ``packs/kb/kb``). The CLI prefers
    Node 22+ — run ``nvm use 22`` first if it complains.
    """
    if PACKS_DIR.exists():
        shutil.rmtree(PACKS_DIR)
    PACKS_DIR.mkdir(parents=True)

    last_err = None
    for cmd in _pack_commands():
        full = cmd + [
            "package", "pack", PACK_NAME,
            "--in", str(SRC_DIR),
            "--out", str(PACKS_DIR),
        ]
        try:
            result = subprocess.run(
                full, cwd=str(REPO_ROOT),
                capture_output=True, text=True, check=False,
            )
        except FileNotFoundError as exc:
            last_err = str(exc)
            continue
        out_pack = PACKS_DIR / PACK_NAME
        if result.returncode == 0 and out_pack.exists() and any(out_pack.iterdir()):
            return result.stdout.strip()
        last_err = (result.stdout + result.stderr).strip() or f"exit {result.returncode}"
    raise RuntimeError(
        "Foundry CLI pack failed. Ensure Node 22+ and @foundryvtt/foundryvtt-cli "
        f"are available (e.g. `nvm use 22`).\nLast error: {last_err}"
    )


# ---------------------------------------------------------------------------
# Image copy
# ---------------------------------------------------------------------------

def copy_images(referenced):
    """Copy referenced hero+gallery images into assets/, preserving subpaths.

    Returns a list of warnings for any missing source (like build_site.copy_images).
    """
    warnings = []
    if ASSETS_DIR.exists():
        shutil.rmtree(ASSETS_DIR)
    if not referenced:
        return warnings
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    for name in sorted(referenced):
        src = IMAGE_SRC_DIR / name
        if not src.exists():
            warnings.append(f"  image source missing: {src.relative_to(REPO_ROOT)}")
            continue
        dest = ASSETS_DIR / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
    return warnings


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def write_src(docs):
    """Wipe and regenerate src/kb, one pretty-printed JSON file per document."""
    import json
    if SRC_DIR.exists():
        shutil.rmtree(SRC_DIR)
    SRC_DIR.mkdir(parents=True)
    for doc in docs:
        # Derive a stable, collision-free filename from the _key.
        key = doc["_key"].strip("!")
        fname = re.sub(r"[^A-Za-z0-9._-]", "_", key) + ".json"
        (SRC_DIR / fname).write_text(
            json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Mirror the campaign KB into the grimwild-kb Foundry compendium.",
    )
    parser.add_argument(
        "--no-pack", action="store_true",
        help="Generate src JSON + copy assets but skip the Foundry CLI pack step.",
    )
    args = parser.parse_args(argv)

    entities = [e for e in load_entities() if e["subdir"] in IN_SCOPE]

    # id_map: entity slug -> deterministic JournalEntry id (for @UUID resolution).
    id_map = {entity_id(e): stable_id(f"journal:{entity_id(e)}") for e in entities}
    alias_map = load_alias_map()

    docs = []

    # Type folders.
    type_folder_id = {}
    for sort, (subdir, label) in enumerate(TYPE_FOLDERS):
        fid = stable_id(f"folder:{label}")
        type_folder_id[subdir] = fid
        docs.append(make_folder(label, fid, sort * 100000))

    # Session arc sub-folders (nested under Sessions), in first-seen order.
    sessions_parent = type_folder_id["sessions"]
    arc_names = {}      # arc_slug -> display name (from the arc index entity)
    arc_order = []      # arc_slug in first-seen order
    for e in entities:
        if e["subdir"] != "sessions":
            continue
        fm = e["fm"] or {}
        arc_slug = fm.get("arc") if fm.get("type") != "arc" else entity_id(e)
        if not arc_slug:
            continue
        if arc_slug not in arc_order:
            arc_order.append(arc_slug)
        if fm.get("type") == "arc":
            arc_names[arc_slug] = entity_name(e)

    arc_folder_id = {}
    for sort, arc_slug in enumerate(arc_order):
        label = arc_names.get(arc_slug) or arc_slug.replace("-", " ").title()
        fid = stable_id(f"folder:sessions:{arc_slug}")
        arc_folder_id[arc_slug] = fid
        docs.append(make_folder(label, fid, sort * 100000, parent=sessions_parent))

    # JournalEntries.
    referenced = set()
    per_type_count = {subdir: 0 for subdir, _ in TYPE_FOLDERS}
    # Stable, name-sorted ordering within each folder.
    entities_sorted = sorted(entities, key=lambda e: (e["subdir"], entity_name(e).lower()))
    sort_counter = {}
    for e in entities_sorted:
        slug = entity_id(e)
        subdir = e["subdir"]
        if subdir == "sessions":
            fm = e["fm"] or {}
            arc_slug = fm.get("arc") if fm.get("type") != "arc" else slug
            folder_id = arc_folder_id.get(arc_slug, sessions_parent)
        else:
            folder_id = type_folder_id[subdir]
        sort = sort_counter.get(folder_id, 0)
        sort_counter[folder_id] = sort + 100000
        docs.append(
            build_journal(e, slug, folder_id, sort, alias_map, id_map, referenced)
        )
        per_type_count[subdir] += 1

    write_src(docs)
    image_warnings = copy_images(referenced)

    n_pages = sum(len(d["pages"]) for d in docs if d["_key"].startswith("!journal!"))
    n_folders = sum(1 for d in docs if d["_key"].startswith("!folders!"))
    n_journals = sum(1 for d in docs if d["_key"].startswith("!journal!"))

    pack_msg = ""
    if not args.no_pack:
        pack_msg = pack_leveldb()

    print(f"Wrote {len(docs)} source docs to {SRC_DIR.relative_to(REPO_ROOT)}")
    print(f"  JournalEntries: {n_journals}  (" +
          ", ".join(f"{label}={per_type_count[s]}" for s, label in TYPE_FOLDERS) + ")")
    print(f"  Folders: {n_folders} ({len(TYPE_FOLDERS)} type + {len(arc_order)} arc)")
    print(f"  Pages: {n_pages}")
    print(f"  Images copied: {len(referenced) - len(image_warnings)} "
          f"to {ASSETS_DIR.relative_to(REPO_ROOT)}")
    if not args.no_pack:
        print(f"  Packed LevelDB → {(PACKS_DIR / PACK_NAME).relative_to(REPO_ROOT)}")
        if pack_msg:
            for line in pack_msg.splitlines():
                print(f"    {line}")
    if image_warnings:
        print(f"\nWarnings ({len(image_warnings)}):")
        for w in image_warnings:
            print(w)

    return str(SRC_DIR)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Build the extraction context manifest for a prepared transcript.

Produces a manifest JSON containing session metadata, known entity lists,
KB filenames, KB sub-entity headers, and campaign context. The extract-session
workflow reads this manifest to ground entity recognition while reading the
full transcript in a single pass.
"""

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SPEAKER_MAP = REPO_ROOT / "config" / "speaker-map.yaml"
DEFAULT_ENTITY_ALIASES = REPO_ROOT / "config" / "entity-aliases.yaml"
MANIFEST_DIR = REPO_ROOT / "inbox" / "transcripts" / "manifest"
KB_ROOT = REPO_ROOT / "kb"
CAMPAIGN_INDEX = REPO_ROOT / "exports" / "campaign-index.md"

KB_SUBDIRS = ["pcs", "npcs", "locations", "items", "factions", "sessions", "story-arcs", "world"]

# KB subdirectories to scan for sub-entity headers (skip sessions and story-arcs)
KB_SCAN_SUBDIRS = ["npcs", "locations", "items", "factions", "world"]

# A header counts as a sub-entity ONLY if it is an explicit wiki-link, e.g.
# `## [[The God of Ruin]]`. This is opt-in (fails closed): structural section
# headers like `## Overview` or `## Potential Story Beats` are plain text and
# are ignored, so new section headers can never leak in as fake entities.
SUBENTITY_HEADER_RE = re.compile(r'^#{2,3}\s+\[\[([^\]]+)\]\]\s*$')


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Build the extraction context manifest for a prepared transcript.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='examples:\n'
               '  %(prog)s --session 2 --input inbox/transcripts/prepared/session-2.txt\n'
               '  %(prog)s --session 3\n',
    )
    parser.add_argument(
        "--session", type=int, required=True,
        help="Session number (required).",
    )
    parser.add_argument(
        "--input", type=str, default=None,
        help="Path to prepared transcript (default: inbox/transcripts/prepared/session-{N}.txt).",
    )
    return parser.parse_args(argv)


def default_prepared_path(session):
    return REPO_ROOT / "inbox" / "transcripts" / "prepared" / f"session-{session}.txt"


def load_yaml(path):
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _title_from_filename(filename):
    """Convert a KB filename to a readable title (e.g., 'old-gods.md' → 'Old Gods')."""
    stem = filename.replace(".md", "")
    return stem.replace("-", " ").title()


def scan_kb_sub_entities():
    """Scan KB markdown files for wiki-link headers that represent sub-entities.

    Only ## / ### headers wrapped in a wiki-link (e.g. `## [[The God of Ruin]]`)
    are treated as sub-entities. Plain structural headers (`## Overview`,
    `## Notable Members`, ...) are ignored. See SUBENTITY_HEADER_RE.

    Returns:
        sub_entity_map: dict mapping header name → {"parent_file", "parent_name", "category"}
        kb_content_hints: dict mapping relative file path → list of sub-entity header names
    """
    sub_entity_map = {}
    kb_content_hints = {}

    for subdir in KB_SCAN_SUBDIRS:
        dir_path = KB_ROOT / subdir
        if not dir_path.is_dir():
            continue
        for md_file in sorted(dir_path.iterdir()):
            if not md_file.is_file() or md_file.suffix != ".md" or md_file.name == ".gitkeep":
                continue
            rel_path = f"{subdir}/{md_file.name}"
            parent_name = _title_from_filename(md_file.name)
            sections = []
            for line in md_file.read_text(encoding="utf-8").splitlines():
                m = SUBENTITY_HEADER_RE.match(line)
                if not m:
                    continue
                # Support `## [[Target|Display]]` — key on the link target.
                header_text = m.group(1).split("|", 1)[0].strip()
                sections.append(header_text)
                if header_text not in sub_entity_map:
                    sub_entity_map[header_text] = {
                        "parent_file": rel_path,
                        "parent_name": parent_name,
                        "category": subdir,
                    }
            if sections:
                kb_content_hints[rel_path] = sections

    return sub_entity_map, kb_content_hints


def collect_known_entities(speaker_map_data, entity_aliases_data, sub_entities=None):
    """Build a dict of known entity names organized by source."""
    entities = {
        "pcs": [],
        "npcs_and_others": [],
        "locations": [],
        "items": [],
        "factions": [],
        "world": [],
    }

    # PCs from speaker-map
    for player_key, player in speaker_map_data.get("players", {}).items():
        for char in player.get("characters", []):
            name = char.get("name", "")
            display = char.get("display", name)
            if name:
                entities["pcs"].append(name)
            if display and display != name:
                entities["pcs"].append(display)

    # Entity aliases by category
    for category in ["characters", "locations", "items", "factions", "world"]:
        aliases = entity_aliases_data.get(category, {})
        target_key = category
        if category == "characters":
            target_key = "npcs_and_others"
        elif category not in entities:
            target_key = "world"
        for alias_name in aliases:
            if alias_name not in entities.get("pcs", []):
                entities[target_key].append(alias_name)

    # Sub-entities from KB file headers
    if sub_entities:
        category_map = {
            "pcs": "pcs",
            "npcs": "npcs_and_others",
            "locations": "locations",
            "items": "items",
            "factions": "factions",
            "world": "world",
        }
        for name, info in sub_entities.items():
            target_key = category_map.get(info["category"], "world")
            entities[target_key].append(name)

    # Deduplicate each list while preserving order
    for key in entities:
        seen = set()
        deduped = []
        for name in entities[key]:
            if name.lower() not in seen:
                seen.add(name.lower())
                deduped.append(name)
        entities[key] = deduped

    return entities


def collect_kb_filenames():
    """List KB filenames by subdirectory."""
    filenames = {}
    for subdir in KB_SUBDIRS:
        dir_path = KB_ROOT / subdir
        if dir_path.is_dir():
            files = sorted(
                f.name for f in dir_path.iterdir()
                if f.is_file() and f.name != ".gitkeep"
            )
            if files:
                filenames[subdir] = files
    return filenames


def load_campaign_context():
    """Read campaign-index.md if it exists."""
    if CAMPAIGN_INDEX.exists():
        return CAMPAIGN_INDEX.read_text(encoding="utf-8")
    return ""


def main(argv=None):
    args = parse_args(argv)

    input_path = (Path(args.input) if args.input else default_prepared_path(args.session)).resolve()
    if not input_path.exists():
        print(f"Error: Prepared transcript not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    # Read transcript (line count only — the extraction workflow reads the full text)
    text = input_path.read_text(encoding="utf-8")
    total_lines = len(text.splitlines())

    # Load configs
    speaker_map_data = load_yaml(DEFAULT_SPEAKER_MAP)
    entity_aliases_data = load_yaml(DEFAULT_ENTITY_ALIASES)

    # Scan KB sub-entities
    sub_entity_map, kb_content_hints = scan_kb_sub_entities()

    # Collect entity info (including sub-entities)
    known_entities = collect_known_entities(speaker_map_data, entity_aliases_data, sub_entities=sub_entity_map)
    kb_filenames = collect_kb_filenames()
    campaign_context = load_campaign_context()

    # Ensure output directory
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)

    # Build manifest
    manifest = {
        "session": args.session,
        "source_transcript": str(input_path.relative_to(REPO_ROOT)),
        "total_lines": total_lines,
        "known_entities": known_entities,
        "kb_filenames": kb_filenames,
        "sub_entity_map": sub_entity_map,
        "kb_content_hints": kb_content_hints,
        "campaign_context": campaign_context,
    }

    manifest_path = MANIFEST_DIR / f"session-{args.session}-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # Summary
    print(f"Built manifest: {manifest_path}")
    print(f"  Source transcript: {input_path}")
    print(f"  Total lines: {total_lines}")
    print(f"  Sub-entities discovered: {len(sub_entity_map)} (from {len(kb_content_hints)} files)")
    print(f"  Known entities: " + ", ".join(f"{k}={len(v)}" for k, v in known_entities.items()))

    return str(manifest_path)


if __name__ == "__main__":
    main()

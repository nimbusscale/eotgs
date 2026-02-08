#!/usr/bin/env python3
"""Split a prepared transcript into chunks for parallel extraction.

Produces numbered chunk files and a manifest JSON containing session metadata,
known entity lists, KB filenames, campaign context, and per-chunk info.
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
CHUNKS_DIR = REPO_ROOT / "inbox" / "transcripts" / "chunks"
KB_ROOT = REPO_ROOT / "grimwild-kb"
CAMPAIGN_INDEX = REPO_ROOT / "exports" / "campaign-index.md"

KB_SUBDIRS = ["pcs", "npcs", "locations", "items", "factions", "sessions", "story-arcs", "world"]


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Split a prepared Grimwild transcript into chunks for extraction.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='examples:\n'
               '  %(prog)s --session 2 --input inbox/transcripts/prepared/session-2.txt\n'
               '  %(prog)s --session 3 --chunk-size 800 --overlap 50\n',
    )
    parser.add_argument(
        "--session", type=int, required=True,
        help="Session number (required).",
    )
    parser.add_argument(
        "--input", type=str, default=None,
        help="Path to prepared transcript (default: inbox/transcripts/prepared/session-{N}.txt).",
    )
    parser.add_argument(
        "--chunk-size", type=int, default=800,
        help="Lines per chunk (default: 800).",
    )
    parser.add_argument(
        "--overlap", type=int, default=50,
        help="Lines of overlap between chunks (default: 50).",
    )
    return parser.parse_args(argv)


def default_prepared_path(session):
    return REPO_ROOT / "inbox" / "transcripts" / "prepared" / f"session-{session}.txt"


def load_yaml(path):
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def collect_known_entities(speaker_map_data, entity_aliases_data):
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


def build_entity_patterns(entities):
    """Build compiled regex patterns for entity mention scanning."""
    all_names = []
    for names in entities.values():
        all_names.extend(names)
    # Sort longest first so longer names match before shorter substrings
    all_names.sort(key=len, reverse=True)
    # Escape and compile as case-insensitive word-boundary patterns
    patterns = []
    for name in all_names:
        try:
            pattern = re.compile(r'\b' + re.escape(name) + r'\b', re.IGNORECASE)
            patterns.append((name, pattern))
        except re.error:
            continue
    return patterns


def scan_chunk_entities(text, patterns):
    """Return set of entity names mentioned in text."""
    found = set()
    for name, pattern in patterns:
        if pattern.search(text):
            found.add(name)
    return sorted(found)


def split_into_chunks(lines, chunk_size, overlap):
    """Split lines into overlapping chunks, returning list of (start, end) ranges (1-indexed)."""
    total = len(lines)
    if total == 0:
        return []

    chunks = []
    start = 0
    while start < total:
        end = min(start + chunk_size, total)
        chunks.append((start, end))
        if end >= total:
            break
        start = end - overlap

    return chunks


def main(argv=None):
    args = parse_args(argv)

    input_path = (Path(args.input) if args.input else default_prepared_path(args.session)).resolve()
    if not input_path.exists():
        print(f"Error: Prepared transcript not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    # Read transcript
    text = input_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    total_lines = len(lines)

    # Load configs
    speaker_map_data = load_yaml(DEFAULT_SPEAKER_MAP)
    entity_aliases_data = load_yaml(DEFAULT_ENTITY_ALIASES)

    # Collect entity info
    known_entities = collect_known_entities(speaker_map_data, entity_aliases_data)
    kb_filenames = collect_kb_filenames()
    campaign_context = load_campaign_context()
    entity_patterns = build_entity_patterns(known_entities)

    # Split into chunks
    chunk_ranges = split_into_chunks(lines, args.chunk_size, args.overlap)

    # Ensure output directory
    CHUNKS_DIR.mkdir(parents=True, exist_ok=True)

    # Write chunk files and build manifest
    chunk_infos = []
    for i, (start, end) in enumerate(chunk_ranges):
        chunk_lines = lines[start:end]
        chunk_text = "\n".join(chunk_lines) + "\n"
        chunk_path = CHUNKS_DIR / f"session-{args.session}-chunk-{i}.txt"
        chunk_path.write_text(chunk_text, encoding="utf-8")

        # Scan for entity mentions in this chunk
        mentioned = scan_chunk_entities(chunk_text, entity_patterns)

        chunk_infos.append({
            "chunk_index": i,
            "file": str(chunk_path.relative_to(REPO_ROOT)),
            "line_start": start + 1,  # 1-indexed
            "line_end": end,           # inclusive
            "line_count": end - start,
            "entities_mentioned": mentioned,
        })

    # Build manifest
    manifest = {
        "session": args.session,
        "source_transcript": str(input_path.relative_to(REPO_ROOT)),
        "total_lines": total_lines,
        "chunk_size": args.chunk_size,
        "overlap": args.overlap,
        "chunk_count": len(chunk_infos),
        "known_entities": known_entities,
        "kb_filenames": kb_filenames,
        "campaign_context": campaign_context,
        "chunks": chunk_infos,
    }

    manifest_path = CHUNKS_DIR / f"session-{args.session}-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # Summary
    print(f"Chunked transcript: {input_path}")
    print(f"  Total lines: {total_lines}")
    print(f"  Chunk size: {args.chunk_size} (overlap: {args.overlap})")
    print(f"  Chunks created: {len(chunk_infos)}")
    for info in chunk_infos:
        print(f"    chunk-{info['chunk_index']}: lines {info['line_start']}-{info['line_end']}"
              f" ({info['line_count']} lines, {len(info['entities_mentioned'])} entities)")
    print(f"  Manifest: {manifest_path}")

    return str(manifest_path)


if __name__ == "__main__":
    main()

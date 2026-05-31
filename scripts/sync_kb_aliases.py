#!/usr/bin/env python3
"""Sync sub-entity names from KB markdown headers into entity-aliases.yaml.

Scans KB files for ## and ### headers that represent sub-entities (e.g.,
"The God of Ruin" inside factions/old-gods.md) and adds missing aliases
to entity-aliases.yaml so that both extraction and incorporation can
resolve sub-entity names to their parent files.
"""

import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_manifest import scan_kb_sub_entities

REPO_ROOT = Path(__file__).resolve().parent.parent
ENTITY_ALIASES_PATH = REPO_ROOT / "config" / "entity-aliases.yaml"

# Map KB subdirectory names to entity-aliases.yaml category keys
SUBDIR_TO_CATEGORY = {
    "npcs": "characters",
    "locations": "locations",
    "items": "items",
    "factions": "factions",
    "world": "world",
}

# Ordered list of categories for consistent YAML output
CATEGORY_ORDER = ["characters", "locations", "items", "factions", "world"]


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Sync KB sub-entity names into entity-aliases.yaml.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be added without writing.",
    )
    return parser.parse_args(argv)


def load_aliases():
    """Load entity-aliases.yaml, returning the parsed dict."""
    if not ENTITY_ALIASES_PATH.exists():
        return {}
    with open(ENTITY_ALIASES_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def build_existing_alias_set(aliases_data):
    """Build a case-insensitive set of all alias names across all categories."""
    existing = set()
    for category in aliases_data.values():
        if isinstance(category, dict):
            for alias_name in category:
                existing.add(alias_name.lower())
    return existing


def write_aliases(aliases_data):
    """Write entity-aliases.yaml with consistent formatting.

    Uses explicit string formatting rather than yaml.dump to preserve
    the double-quoted key style used in the existing file.
    """
    lines = [
        "# Maps alternative names/spellings to canonical entity filenames",
        "# Used during KB incorporation to find existing entries",
        "",
    ]

    for category in CATEGORY_ORDER:
        entries = aliases_data.get(category)
        if not entries:
            continue
        lines.append(f"{category}:")
        for alias_name, slug in entries.items():
            lines.append(f'  "{alias_name}": "{slug}"')
        lines.append("")

    ENTITY_ALIASES_PATH.write_text("\n".join(lines), encoding="utf-8")


def main(argv=None):
    args = parse_args(argv)

    # Scan KB for sub-entities (already excludes pcs via KB_SCAN_SUBDIRS)
    sub_entity_map, _ = scan_kb_sub_entities()

    # Load current aliases
    aliases_data = load_aliases()
    existing_names = build_existing_alias_set(aliases_data)

    # Find missing sub-entities
    additions = []
    for name, info in sorted(sub_entity_map.items()):
        category_key = SUBDIR_TO_CATEGORY.get(info["category"])
        if not category_key:
            continue

        # Skip if already aliased (case-insensitive)
        if name.lower() in existing_names:
            continue

        # Derive slug from parent filename
        slug = info["parent_file"].split("/")[-1].replace(".md", "")

        # Ensure category section exists
        if category_key not in aliases_data:
            aliases_data[category_key] = {}

        aliases_data[category_key][name] = slug
        existing_names.add(name.lower())
        additions.append((category_key, name, slug))

    if not additions:
        print("No new aliases needed.")
        return str(ENTITY_ALIASES_PATH)

    if args.dry_run:
        print(f"Would add {len(additions)} alias(es):")
        for cat, name, slug in additions:
            print(f"  {cat}: \"{name}\" → \"{slug}\"")
        return str(ENTITY_ALIASES_PATH)

    write_aliases(aliases_data)

    print(f"Added {len(additions)} alias(es) to {ENTITY_ALIASES_PATH.name}:")
    for cat, name, slug in additions:
        print(f"  {cat}: \"{name}\" → \"{slug}\"")

    return str(ENTITY_ALIASES_PATH)


if __name__ == "__main__":
    main()

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


def render_aliases(aliases_data):
    """Render entity-aliases.yaml text with consistent formatting.

    Uses explicit string formatting rather than yaml.dump to preserve
    the double-quoted key style used in the existing file. Returns the
    full file text so callers can either write it or diff against it.
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

    return "\n".join(lines)


def write_aliases(aliases_data):
    """Write entity-aliases.yaml with consistent formatting."""
    ENTITY_ALIASES_PATH.write_text(render_aliases(aliases_data), encoding="utf-8")


def main(argv=None):
    """Deprecation shim.

    entity-aliases.yaml is no longer synced incrementally from KB headers — it
    is *generated* (along with image-map.yaml and subject-index.yaml) from the
    per-entity frontmatter in kb/**/*.md by scripts/build_index.py. This entry
    point now delegates there so any lingering callers keep working. The
    formatting helpers above (render_aliases, write_aliases, CATEGORY_ORDER,
    SUBDIR_TO_CATEGORY) are still imported and reused by build_index.
    """
    args = parse_args(argv)
    print(
        "sync_kb_aliases.py is deprecated: entity-aliases.yaml is generated from "
        "per-entity KB frontmatter by scripts/build_index.py. Delegating to it.",
        file=sys.stderr,
    )
    from build_index import main as build_index_main

    return build_index_main(argv=["--check"] if args.dry_run else [])


if __name__ == "__main__":
    main()

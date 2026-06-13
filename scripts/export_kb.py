#!/usr/bin/env python3
"""Export the campaign KB into consolidated files for Claude Projects.

Generates 7 mechanical export files from the knowledge base:
  characters-pcs.md      characters-npcs.md    locations.md
  world-setting.md       sessions.md           hooks-all.md
  gm-notes.md

The 8th file (campaign-index.md) requires LLM synthesis and is handled
separately by the /export-kb Claude Code skill.

Note: active story arcs now live in kb/sessions/<arc>/index.md and reach the
export bundle via campaign-index.md (synthesized) and sessions.md.
Character hooks live in each PC's `## Hooks` section and reach the bundle via
characters-pcs.md. hooks-all.md therefore covers group hooks only.
"""

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
KB_DIR = REPO_ROOT / "kb"
GM_DIR = REPO_ROOT / "gm-notes"
EXPORTS_DIR = REPO_ROOT / "exports"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Export campaign KB to consolidated files for Claude Projects.",
    )
    parser.add_argument(
        "--sessions", type=int, default=None,
        help="Number of recent sessions to include (default: all)",
    )
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def demote_headers(text, levels=1):
    """Shift markdown ``#`` headers down by *levels* (e.g. ``# → ##``)."""
    def _bump(m):
        return "#" * min(len(m.group(1)) + levels, 6) + m.group(2)
    return re.sub(r"^(#{1,6})([ \t])", _bump, text, flags=re.MULTILINE)


def read_and_demote(path, levels=1):
    """Read a markdown file and demote its headers by *levels*."""
    return demote_headers(path.read_text(encoding="utf-8"), levels)


def session_sort_key(path):
    """Extract the numeric session number from a path for sorting."""
    m = re.search(r"session-(\d+)", path.name)
    return int(m.group(1)) if m else 0


def get_md_files(directory, exclude=None):
    """Return alphabetically sorted ``.md`` files, optionally excluding names."""
    if not directory.exists():
        return []
    files = sorted(directory.glob("*.md"))
    if exclude:
        files = [f for f in files if f.name not in exclude]
    return files


def strip_top_header(text):
    """Remove the first ``# …`` line and any blank lines right after it."""
    return re.sub(r"^# .+\n\n*", "", text, count=1)


def count_hooks(text):
    """Count ``## `` headers (each is one hook) in a hooks file."""
    return len(re.findall(r"^## ", text, re.MULTILINE))


# ---------------------------------------------------------------------------
# Per-file export functions
# Each returns (content_str, entry_description_str).
# ---------------------------------------------------------------------------

def export_pcs():
    files = get_md_files(KB_DIR / "pcs")
    parts = ["# Player Characters"]
    for f in files:
        parts.append(read_and_demote(f, 1).strip())
    return "\n\n\n".join(parts) + "\n", f"{len(files)} PCs"


def export_npcs():
    files = get_md_files(KB_DIR / "npcs")
    parts = ["# Non-Player Characters"]
    for f in files:
        parts.append(read_and_demote(f, 1).strip())
    return "\n\n\n".join(parts) + "\n", f"{len(files)} NPCs"


def export_locations():
    files = get_md_files(KB_DIR / "locations")
    parts = ["# Locations"]
    for f in files:
        parts.append(read_and_demote(f, 1).strip())
    return "\n\n\n".join(parts) + "\n", f"{len(files)} locations"


def export_world_setting():
    world_files = get_md_files(KB_DIR / "world")
    faction_files = get_md_files(KB_DIR / "factions")
    item_files = get_md_files(KB_DIR / "items")

    parts = ["# World Setting"]
    for f in world_files:
        parts.append(read_and_demote(f, 1).strip())

    # Factions sub-section (demoted 2 levels so entries sit under ## Factions)
    if faction_files:
        entries = [read_and_demote(f, 2).strip() for f in faction_files]
        parts.append("## Factions\n\n" + "\n\n\n".join(entries))
    else:
        parts.append("## Factions")

    # Items sub-section
    if item_files:
        entries = [read_and_demote(f, 2).strip() for f in item_files]
        parts.append("## Notable Items\n\n" + "\n\n\n".join(entries))
    else:
        parts.append("## Notable Items")

    counts = (
        f"{len(world_files)} world + {len(faction_files)} factions"
        f" + {len(item_files)} items"
    )
    return "\n\n\n".join(parts) + "\n", counts


def export_sessions(session_count=None):
    sessions_dir = KB_DIR / "sessions"
    # Sessions now live nested under arc folders: sessions/<arc>/session-N.md
    # Match any file whose stem starts with "session-" (excludes arc index.md).
    all_sessions = [
        f for f in sessions_dir.rglob("session-*.md")
    ] if sessions_dir.exists() else []
    files = sorted(all_sessions, key=session_sort_key, reverse=True)
    # session_count=None (or 0) includes every session; otherwise cap to the N most recent.
    if session_count:
        files = files[:session_count]

    parts = ["# Sessions"]
    for f in files:
        parts.append(read_and_demote(f, 1).strip())
    return "\n\n\n".join(parts) + "\n", f"{len(files)} sessions"


def export_hooks():
    """Export group-level story hooks.

    Character hooks live in each PC's `## Hooks` section and already reach the
    bundle via characters-pcs.md, so they are intentionally not duplicated here.
    """
    group_file = KB_DIR / "story-arcs" / "group" / "hooks.md"
    group_count = 0

    sections = [
        "# Story Hooks\n\n"
        "These are open group-level threads and unresolved mysteries "
        "that could develop into future story arcs. "
        "(Character-specific hooks live in each PC entry.)"
    ]

    if group_file.exists():
        raw = group_file.read_text(encoding="utf-8")
        group_count = count_hooks(raw)
        content = demote_headers(strip_top_header(raw), 1).strip()
        sections.append("## Group Hooks\n\n" + content)
    else:
        sections.append("## Group Hooks")

    return "\n\n".join(sections) + "\n", f"{group_count} group hooks"


def export_gm_notes():
    files = get_md_files(GM_DIR)
    parts = [
        "# GM Notes\n\n"
        "> **GM ONLY** - This file contains secrets and planning material "
        "not for player eyes."
    ]
    for f in files:
        parts.append(read_and_demote(f, 1).strip())
    return "\n\n\n".join(parts) + "\n", f"{len(files)} files"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv=None):
    args = parse_args(argv)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

    exports = [
        ("characters-pcs.md",    export_pcs),
        ("characters-npcs.md",   export_npcs),
        ("locations.md",         export_locations),
        ("world-setting.md",     export_world_setting),
        ("sessions.md",          lambda: export_sessions(args.sessions)),
        ("hooks-all.md",         export_hooks),
        ("gm-notes.md",         export_gm_notes),
    ]

    results = []
    total_size = 0
    for filename, func in exports:
        content, counts = func()
        path = EXPORTS_DIR / filename
        path.write_text(content, encoding="utf-8")
        size = len(content.encode("utf-8"))
        total_size += size
        results.append((filename, size, counts))

    # ---- summary table ----
    print("\n## Export Complete\n")
    print("**Files generated:**")
    print("| File | Size | Entries |")
    print("|------|------|---------|")
    for filename, size, counts in results:
        print(f"| {filename} | {size / 1024:.1f} KB | {counts} |")
    print(f"\n**Total export size:** {total_size / 1024:.1f} KB")
    print(
        "\n**Note:** campaign-index.md requires LLM synthesis"
        " \u2014 run /export-kb to generate it."
    )

    return str(EXPORTS_DIR)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Export the campaign KB into consolidated files for Claude Projects.

Generates 8 mechanical export files from the knowledge base:
  characters-pcs.md      characters-npcs.md    locations.md
  world-setting.md       story-arcs-active.md  sessions-recent.md
  hooks-all.md           gm-notes.md

The 9th file (campaign-index.md) requires LLM synthesis and is handled
separately by the /export-kb Claude Code skill.
"""

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
KB_DIR = REPO_ROOT / "kb"
GM_DIR = REPO_ROOT / "gm-notes"
EXPORTS_DIR = REPO_ROOT / "exports"

SMALL_WORDS = {
    "a", "an", "and", "as", "at", "but", "by", "for", "if", "in",
    "nor", "of", "on", "or", "so", "the", "to", "up", "via", "yn", "with",
}


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Export campaign KB to consolidated files for Claude Projects.",
    )
    parser.add_argument(
        "--sessions", type=int, default=5,
        help="Number of recent sessions to include (default: 5)",
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


def slugname_to_title(slug):
    """Convert a filename slug to title case.

    Keeps small words (yn, of, the …) lowercase except at position 0.
    ``'garland-yn-greenholt'`` → ``'Garland yn Greenholt'``
    """
    words = slug.split("-")
    return " ".join(
        w if (i > 0 and w in SMALL_WORDS) else w.capitalize()
        for i, w in enumerate(words)
    )


def get_status(text):
    """Return the value after ``**Status:**``, or *None*."""
    m = re.search(r"\*\*Status:\*\*\s*(.+)", text)
    return m.group(1).strip() if m else None


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


def extract_title(text):
    """Return the text after the first ``# `` header, or *None*."""
    m = re.match(r"^# (.+)", text, re.MULTILINE)
    return m.group(1).strip() if m else None


def transform_arc(text, title_override=None):
    """Reshape a story-arc source file for the consolidated export.

    * ``# Title`` → ``### Title`` (or *title_override*)
    * ``## Summary`` header is stripped (content kept inline)
    * Other ``## Foo`` → ``**Foo:**`` (skipped if the section body is empty)
    """
    lines = text.split("\n")

    # Parse into title, metadata, and named sections
    title = None
    metadata = []
    sections = []          # [(name, [lines …]), …]
    cur_name = None
    cur_lines = []

    for line in lines:
        if title is None and line.startswith("# "):
            title = line[2:].strip()
            continue
        if line.startswith("## "):
            if cur_name is not None:
                sections.append((cur_name, cur_lines))
            cur_name = line[3:].strip()
            cur_lines = []
            continue
        if cur_name is None:
            metadata.append(line)
        else:
            cur_lines.append(line)
    if cur_name is not None:
        sections.append((cur_name, cur_lines))

    # Trim trailing blank lines from metadata
    while metadata and metadata[-1].strip() == "":
        metadata.pop()

    # Build output
    result = [f"### {title_override or title}"]
    result.extend(metadata)

    for name, body in sections:
        content = "\n".join(body).strip()
        if name == "Summary":
            if content:
                result.append("")
                result.append(content)
        else:
            if content:
                result.append("")
                result.append(f"**{name}:**")
                result.append(content)

    return "\n".join(result)


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


def export_story_arcs():
    group_dir = KB_DIR / "story-arcs" / "group"
    char_base = KB_DIR / "story-arcs" / "character"

    # --- group arcs ---
    group_arcs = []
    for f in get_md_files(group_dir, exclude={"hooks.md"}):
        text = f.read_text(encoding="utf-8")
        status = get_status(text)
        if status and "Active" in status:
            group_arcs.append(transform_arc(text).strip())

    # --- character arcs ---
    char_arcs = []
    if char_base.exists():
        for d in sorted(char_base.iterdir()):
            if not d.is_dir():
                continue
            char_name = slugname_to_title(d.name)
            for f in get_md_files(d, exclude={"hooks.md"}):
                text = f.read_text(encoding="utf-8")
                status = get_status(text)
                if status and "Active" in status:
                    arc_title = extract_title(text) or f.stem
                    override = f"{char_name} \u2014 {arc_title}"
                    char_arcs.append(transform_arc(text, override).strip())

    total = len(group_arcs) + len(char_arcs)

    # assemble
    parts = ["# Active Story Arcs"]
    if group_arcs:
        parts.append("## Group Arcs\n\n" + "\n\n\n".join(group_arcs))
    else:
        parts.append("## Group Arcs")

    if char_arcs:
        parts.append("## Character Arcs\n\n" + "\n\n\n".join(char_arcs))
    else:
        parts.append("## Character Arcs")

    return "\n\n\n".join(parts) + "\n", f"{total} arcs"


def export_sessions(session_count=5):
    sessions_dir = KB_DIR / "sessions"
    # Sessions now live nested under arc folders: sessions/<arc>/session-N.md
    # Match any file whose stem starts with "session-" (excludes arc index.md).
    all_sessions = [
        f for f in sessions_dir.rglob("session-*.md")
    ] if sessions_dir.exists() else []
    files = sorted(all_sessions, key=session_sort_key, reverse=True)[:session_count]

    parts = ["# Recent Sessions"]
    for f in files:
        parts.append(read_and_demote(f, 1).strip())
    return "\n\n\n".join(parts) + "\n", f"{len(files)} sessions"


def export_hooks():
    group_file = KB_DIR / "story-arcs" / "group" / "hooks.md"
    char_base = KB_DIR / "story-arcs" / "character"
    group_count = 0
    char_count = 0

    sections = [
        "# Story Hooks\n\n"
        "These are open threads and unresolved mysteries "
        "that could develop into future story arcs."
    ]

    # Group hooks
    if group_file.exists():
        raw = group_file.read_text(encoding="utf-8")
        group_count = count_hooks(raw)
        content = demote_headers(strip_top_header(raw), 1).strip()
        sections.append("## Group Hooks\n\n" + content)
    else:
        sections.append("## Group Hooks")

    # Character hooks
    char_bits = ["## Character Hooks"]
    if char_base.exists():
        for d in sorted(char_base.iterdir()):
            if not d.is_dir():
                continue
            hf = d / "hooks.md"
            if not hf.exists():
                continue
            name = slugname_to_title(d.name)
            raw = hf.read_text(encoding="utf-8")
            char_count += count_hooks(raw)
            content = demote_headers(strip_top_header(raw), 2).strip()
            char_bits.append(f"### {name}\n\n" + content)
    sections.append("\n\n".join(char_bits))

    counts = f"{group_count} group + {char_count} character hooks"
    return "\n\n".join(sections) + "\n", counts


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
        ("story-arcs-active.md", export_story_arcs),
        ("sessions-recent.md",   lambda: export_sessions(args.sessions)),
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

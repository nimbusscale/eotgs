#!/usr/bin/env python3
"""Build the Quartz site content from the campaign KB.

Copies KB files into site/content/, injects YAML frontmatter with aliases
and tags, and generates the landing page index. Does NOT build the static
HTML — that's handled by `npx quartz build` afterwards.
"""

import re
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
KB_DIR = REPO_ROOT / "kb"
SITE_DIR = REPO_ROOT / "site"
CONTENT_DIR = SITE_DIR / "content"
CONTENT_SRC_DIR = REPO_ROOT / "content"
SITE_CONFIG_DIR = Path(__file__).resolve().parent / "site-config"
ALIASES_FILE = REPO_ROOT / "config" / "entity-aliases.yaml"
INDEX_SOURCE = REPO_ROOT / "exports" / "campaign-index.md"

QUARTZ_REPO = "https://github.com/jackyzha0/quartz.git"

# Map subdirectory names to tags
DIR_TO_TAG = {
    "pcs": "pc",
    "npcs": "npc",
    "locations": "location",
    "items": "item",
    "factions": "faction",
    "world": "world",
    "sessions": "session",
    # "story-arcs": "story-arc",  # excluded from site nav; will be restructured
}

SMALL_WORDS = {
    "a", "an", "and", "as", "at", "but", "by", "for", "if", "in",
    "nor", "of", "on", "or", "so", "the", "to", "up", "via", "yn", "with",
}


def slugify_name(name):
    """Convert a display name to a filename slug (lowercase, hyphens, no articles/punctuation)."""
    s = name.lower().strip()
    # Drop leading articles
    s = re.sub(r"^(the|a|an)\s+", "", s)
    # Remove punctuation except hyphens
    s = re.sub(r"[^\w\s-]", "", s)
    # Replace whitespace with hyphens
    s = re.sub(r"\s+", "-", s)
    return s


def build_wikilink_map():
    """Build a lookup from display names to content-relative paths for wiki-link resolution."""
    # 1. Scan KB_DIR for all .md files → {slug: "subdir/slug"} (no .md extension)
    slug_to_path = {}
    slug_to_title = {}
    for md_file in KB_DIR.rglob("*.md"):
        rel = md_file.relative_to(KB_DIR)
        # Path without .md extension, using forward slashes
        rel_path = str(rel.with_suffix("")).replace("\\", "/")
        slug = md_file.stem
        slug_to_path[slug] = rel_path

        # Extract H1 title from file
        text = md_file.read_text(encoding="utf-8")
        title = extract_title(text)
        if title:
            slug_to_title[slug] = title

    # 2. Build the wikilink map: {display_name: relative_path}
    wikilink_map = {}

    # Load the forward alias map from entity-aliases.yaml
    if ALIASES_FILE.exists():
        with open(ALIASES_FILE, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        for category in data.values():
            if not isinstance(category, dict):
                continue
            for alias, slug in category.items():
                if slug in slug_to_path:
                    wikilink_map[alias] = slug_to_path[slug]

    # Also map article-stripped forms of aliases (e.g., "Farus Lucis" from "The Farus Lucis")
    for alias in list(wikilink_map):
        stripped = re.sub(r"^(?:The|A|An)\s+", "", alias)
        if stripped != alias and stripped not in wikilink_map:
            wikilink_map[stripped] = wikilink_map[alias]

    # Map each slug directly (e.g., "nodrum" → "locations/nodrum")
    for slug, path in slug_to_path.items():
        if slug not in wikilink_map:
            wikilink_map[slug] = path

    # Map each file's H1 title (e.g., "The Nodrum" → "locations/nodrum")
    for slug, title in slug_to_title.items():
        if title not in wikilink_map and slug in slug_to_path:
            wikilink_map[title] = slug_to_path[slug]

    # Build a case-insensitive slugified lookup as fallback
    # Maps slugified form of name → path (e.g., "session-2" → "sessions/session-2")
    slug_form_map = {}
    for slug, path in slug_to_path.items():
        slug_form_map[slug] = path
    # Don't overwrite explicit entries — this is only used as fallback in resolve_wikilinks

    return wikilink_map, slug_form_map


_WIKILINK_RE = re.compile(r"\[\[([^\]|]+?)(?:\|([^\]]+?))?\]\]")


def resolve_wikilinks(text, wikilink_map, slug_form_map):
    """Resolve wiki-links to full content-relative paths for Quartz."""

    def _replace(m):
        raw_target = m.group(1).strip()
        alias = m.group(2)

        # Already has a path separator — leave it alone
        if "/" in raw_target:
            return m.group(0)

        # Split off anchor (e.g., "Old Gods and New Gods#The Suppression")
        if "#" in raw_target:
            target, anchor = raw_target.split("#", 1)
            target = target.strip()
            anchor = "#" + anchor.strip()
        else:
            target = raw_target
            anchor = ""

        display = alias.strip() if alias else target  # use target (without anchor), not raw_target

        # Lookup priority:
        # 1. Exact match in wikilink_map (aliases + titles)
        path = wikilink_map.get(target)
        # 2. Slugified form lookup
        if path is None:
            path = slug_form_map.get(slugify_name(target))
        # 3. Lowercase exact match (handles case mismatches)
        if path is None:
            target_lower = target.lower()
            for key, val in wikilink_map.items():
                if key.lower() == target_lower:
                    path = val
                    break

        if path is None:
            return display  # Render as plain text, not a broken link

        return f"[[{path}{anchor}|{display}]]"

    return _WIKILINK_RE.sub(_replace, text)


def slugname_to_title(slug):
    """Convert a filename slug to title case."""
    words = slug.split("-")
    return " ".join(
        w if (i > 0 and w in SMALL_WORDS) else w.capitalize()
        for i, w in enumerate(words)
    )


def extract_title(text):
    """Return the text after the first `# ` header, or None."""
    m = re.match(r"^# (.+)", text, re.MULTILINE)
    return m.group(1).strip() if m else None


def strip_title_heading(text):
    """Remove the first H1 heading line from markdown text."""
    return re.sub(r"^# .+\n?", "", text, count=1)


def strip_summary_section(text):
    """Remove the ## Summary section from markdown text."""
    return re.sub(r"^## Summary\n.*?(?=^## |\Z)", "", text, flags=re.MULTILINE | re.DOTALL)


def build_reverse_alias_map():
    """Read entity-aliases.yaml, return {slug: [alias1, alias2, ...]}."""
    if not ALIASES_FILE.exists():
        return {}
    with open(ALIASES_FILE, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    reverse = defaultdict(list)
    for category in data.values():
        if not isinstance(category, dict):
            continue
        for alias, slug in category.items():
            reverse[slug].append(alias)
    return dict(reverse)


def resolve_tag(rel_path):
    """Derive a tag from the file's subdirectory path."""
    parts = rel_path.parts
    if len(parts) < 2:
        return None
    top_dir = parts[0]
    return DIR_TO_TAG.get(top_dir)


def disambiguate_hooks_title(rel_path):
    """Generate a distinct title for hooks.md files based on their location.

    story-arcs/group/hooks.md          → "Group - Story Hooks"
    story-arcs/character/castor/hooks.md → "Castor - Story Hooks"
    """
    parts = rel_path.parts
    if parts[-1] != "hooks.md":
        return None
    if "character" in parts:
        # e.g. story-arcs/character/castor/hooks.md
        char_slug = parts[parts.index("character") + 1]
        return f"{slugname_to_title(char_slug)} - Story Hooks"
    if "group" in parts:
        return "Group - Story Hooks"
    return "Story Hooks"


def extract_date_played(text):
    """Extract the date from a **Date Played:** line, if present."""
    m = re.search(r"\*\*Date Played:\*\*\s*(\d{4}-\d{2}-\d{2})", text)
    return m.group(1) if m else None


def inject_frontmatter(text, title, aliases, tag, date=None):
    """Prepend YAML frontmatter to markdown content."""
    fm = {"title": title}
    if aliases:
        fm["aliases"] = aliases
    if tag:
        fm["tags"] = [tag]
    if date:
        fm["date"] = date

    fm_str = yaml.dump(fm, default_flow_style=False, allow_unicode=True, sort_keys=False).strip()
    return f"---\n{fm_str}\n---\n\n{text}"


def build_content(alias_map, wikilink_map, slug_form_map):
    """Copy KB files to content dir, injecting frontmatter. Returns stats."""
    copied = 0
    warnings = []

    # Track which slugs actually have files
    existing_slugs = set()

    # Directories to exclude from site content
    excluded_dirs = {"story-arcs"}

    for md_file in KB_DIR.rglob("*.md"):
        rel = md_file.relative_to(KB_DIR)

        # Skip excluded directories
        if rel.parts[0] in excluded_dirs:
            continue

        existing_slugs.add(md_file.stem)

        dest = CONTENT_DIR / rel
        dest.parent.mkdir(parents=True, exist_ok=True)

        text = md_file.read_text(encoding="utf-8")

        # Determine title
        hooks_title = disambiguate_hooks_title(rel)
        if hooks_title:
            title = hooks_title
            # Replace the generic "# Hooks" heading with the specific title
            text = re.sub(r"^# Hooks\b", f"# {hooks_title}", text, count=1)
        else:
            title = extract_title(text) or slugname_to_title(md_file.stem)

        # Get aliases for this file's slug
        aliases = alias_map.get(md_file.stem, [])

        # Get tag from directory
        tag = resolve_tag(rel)

        # Extract date for session files
        date = extract_date_played(text) if tag == "session" else None

        # Strip summary section from session files (kept in KB exports for AI context)
        if tag == "session":
            text = strip_summary_section(text)

        # Resolve wiki-links to full paths before stripping headings
        text = resolve_wikilinks(text, wikilink_map, slug_form_map)

        # Strip H1 heading (Quartz renders title from frontmatter)
        text = strip_title_heading(text)

        # Inject frontmatter
        text = inject_frontmatter(text, title, aliases, tag, date)

        dest.write_text(text, encoding="utf-8")
        copied += 1

    # Warn about aliases pointing to non-existent files
    for slug, names in alias_map.items():
        if slug not in existing_slugs:
            warnings.append(f"  alias target '{slug}' has no file (aliases: {names})")

    return copied, warnings


def extract_pc_cards():
    """Read PC files and build character card markdown blocks.

    Extracts the title and concept section from each PC file.
    Returns a single markdown string with all cards.
    """
    pcs_dir = KB_DIR / "pcs"
    if not pcs_dir.exists():
        return ""

    cards = []
    for pc_file in sorted(pcs_dir.glob("*.md")):
        text = pc_file.read_text(encoding="utf-8")

        # Extract title from first heading
        title = extract_title(text)
        if not title:
            title = slugname_to_title(pc_file.stem)

        # Extract concept section — lines between ## Concept and the next ##
        concept_match = re.search(
            r"^## Concept\n(.+?)(?=\n## |\Z)", text, re.MULTILINE | re.DOTALL
        )
        concept = concept_match.group(1).strip() if concept_match else ""

        card = f"### [[{title}]]\n{concept}"
        cards.append(card)

    return "\n\n".join(cards)


def copy_site_content(wikilink_map, slug_form_map):
    """Copy content/*.md (except home.md) to site/content/, injecting frontmatter."""
    if not CONTENT_SRC_DIR.exists():
        return 0

    copied = 0
    for md_file in CONTENT_SRC_DIR.glob("*.md"):
        if md_file.name == "home.md":
            continue

        text = md_file.read_text(encoding="utf-8")
        title = extract_title(text) or slugname_to_title(md_file.stem)
        text = resolve_wikilinks(text, wikilink_map, slug_form_map)
        text = strip_title_heading(text)
        text = inject_frontmatter(text, title, [], None)

        dest = CONTENT_DIR / md_file.name
        dest.write_text(text, encoding="utf-8")
        copied += 1

    return copied


def create_index(wikilink_map, slug_form_map):
    """Build the landing page from content/home.md with character cards.

    Falls back to campaign-index.md if content/home.md doesn't exist.
    """
    home_src = CONTENT_SRC_DIR / "home.md"
    if home_src.exists():
        text = home_src.read_text(encoding="utf-8")
        # Replace character cards placeholder
        cards = extract_pc_cards()
        text = text.replace("<!-- CHARACTER_CARDS -->", cards)
        title = extract_title(text) or "Echoes of the Godstorm"
        text = resolve_wikilinks(text, wikilink_map, slug_form_map)
        text = strip_title_heading(text)
        text = inject_frontmatter(text, title, [], None)
        (CONTENT_DIR / "index.md").write_text(text, encoding="utf-8")
        return True

    # Fallback: use campaign-index.md
    if not INDEX_SOURCE.exists():
        print(f"Warning: {INDEX_SOURCE} not found, skipping index generation")
        return False
    text = INDEX_SOURCE.read_text(encoding="utf-8")
    title = extract_title(text) or "Echoes of the Godstorm"
    text = resolve_wikilinks(text, wikilink_map, slug_form_map)
    text = strip_title_heading(text)
    text = inject_frontmatter(text, title, [], None)
    (CONTENT_DIR / "index.md").write_text(text, encoding="utf-8")
    return True


def bootstrap_quartz():
    """Clone Quartz and apply our customizations if site/ doesn't exist."""
    if (SITE_DIR / "package.json").exists():
        return

    print("Bootstrapping Quartz...")
    if SITE_DIR.exists():
        shutil.rmtree(SITE_DIR)

    subprocess.run(["git", "clone", QUARTZ_REPO, str(SITE_DIR)], check=True)

    # Remove Quartz's own .git so it doesn't conflict with our repo
    quartz_git = SITE_DIR / ".git"
    if quartz_git.exists():
        shutil.rmtree(quartz_git)

    # Apply our config overrides
    for config_file in SITE_CONFIG_DIR.glob("*"):
        dest = SITE_DIR / config_file.name
        shutil.copy2(config_file, dest)
        print(f"  Applied {config_file.name}")

    # Patch glob.ts to disable gitignore (our content/ is gitignored by the parent repo)
    glob_ts = SITE_DIR / "quartz" / "util" / "glob.ts"
    text = glob_ts.read_text(encoding="utf-8")
    text = text.replace("gitignore: true", "gitignore: false")
    glob_ts.write_text(text, encoding="utf-8")
    print("  Patched glob.ts (disabled gitignore)")

    # Install dependencies (requires Node 22)
    subprocess.run(["npm", "install"], cwd=str(SITE_DIR), check=True)
    print("Quartz bootstrapped successfully")


def main(argv=None):
    # Bootstrap Quartz if needed
    bootstrap_quartz()

    # Clean and recreate content dir
    if CONTENT_DIR.exists():
        shutil.rmtree(CONTENT_DIR)
    CONTENT_DIR.mkdir(parents=True)

    # Build alias map
    alias_map = build_reverse_alias_map()
    print(f"Loaded {sum(len(v) for v in alias_map.values())} aliases across {len(alias_map)} entities")

    # Build wiki-link resolution map
    wikilink_map, slug_form_map = build_wikilink_map()
    print(f"Built wikilink map with {len(wikilink_map)} entries")

    # Copy and transform KB files
    copied, warnings = build_content(alias_map, wikilink_map, slug_form_map)
    print(f"Copied {copied} files to {CONTENT_DIR.relative_to(REPO_ROOT)}")

    # Copy hand-authored site content
    content_copied = copy_site_content(wikilink_map, slug_form_map)
    if content_copied:
        print(f"Copied {content_copied} content files from content/")

    # Create landing page
    if create_index(wikilink_map, slug_form_map):
        src = "content/home.md" if (CONTENT_SRC_DIR / "home.md").exists() else "campaign-index.md"
        print(f"Created index.md from {src}")

    # Print warnings
    if warnings:
        print(f"\nWarnings ({len(warnings)}):")
        for w in warnings:
            print(w)

    return str(CONTENT_DIR)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Build the Quartz site content from the Grimwild KB.

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
KB_DIR = REPO_ROOT / "grimwild-kb"
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
    "story-arcs": "story-arc",
}

SMALL_WORDS = {
    "a", "an", "and", "as", "at", "but", "by", "for", "if", "in",
    "nor", "of", "on", "or", "so", "the", "to", "up", "via", "yn", "with",
}


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


def build_content(alias_map):
    """Copy KB files to content dir, injecting frontmatter. Returns stats."""
    copied = 0
    warnings = []

    # Track which slugs actually have files
    existing_slugs = set()

    for md_file in KB_DIR.rglob("*.md"):
        rel = md_file.relative_to(KB_DIR)
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


def copy_site_content():
    """Copy content/*.md (except home.md) to site/content/, injecting frontmatter."""
    if not CONTENT_SRC_DIR.exists():
        return 0

    copied = 0
    for md_file in CONTENT_SRC_DIR.glob("*.md"):
        if md_file.name == "home.md":
            continue

        text = md_file.read_text(encoding="utf-8")
        title = extract_title(text) or slugname_to_title(md_file.stem)
        text = inject_frontmatter(text, title, [], None)

        dest = CONTENT_DIR / md_file.name
        dest.write_text(text, encoding="utf-8")
        copied += 1

    return copied


def create_index():
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
        text = inject_frontmatter(text, title, [], None)
        (CONTENT_DIR / "index.md").write_text(text, encoding="utf-8")
        return True

    # Fallback: use campaign-index.md
    if not INDEX_SOURCE.exists():
        print(f"Warning: {INDEX_SOURCE} not found, skipping index generation")
        return False
    text = INDEX_SOURCE.read_text(encoding="utf-8")
    title = extract_title(text) or "Echoes of the Godstorm"
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

    # Copy and transform KB files
    copied, warnings = build_content(alias_map)
    print(f"Copied {copied} files to {CONTENT_DIR.relative_to(REPO_ROOT)}")

    # Copy hand-authored site content
    content_copied = copy_site_content()
    if content_copied:
        print(f"Copied {content_copied} content files from content/")

    # Create landing page
    if create_index():
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

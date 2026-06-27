#!/usr/bin/env python3
"""Extract player-character sheets from Foundry into inbox/characters/ snapshots.

The "Echoes of the Godstorm" world runs the Chasing Adventure ruleset on
Foundry's generic ``pbta`` system. Players edit their sheets between games
(adding moves, leveling, adjusting stats). ``scripts/pull_actors.sh`` copies the
world's actors LevelDB down and unpacks it to JSON; this script reads that JSON
and writes one human-readable snapshot per mapped PC to ``inbox/characters/``.

It does NOT touch the kb/pcs/ entries. The snapshots are then folded into each
character entry by judgment via the ``/incorporate-characters`` command (which
reconciles names, weaves stats/moves into the existing sections, and avoids
duplication) — the same extract→incorporate pattern used for sessions and notes.

Scope is the persistent build: playbook/level/xp/armor, stats (STR/DEX/INT/WIS/
CHA), moves, and equipment ("assets"). The universal basic moves every character
carries (the ``adventure`` and ``peripheral`` move types) are filtered out as
noise; playbook and custom moves keep their rules text, and subsystem moves
(favor/chase/follower) are listed by name. Transient conditions are skipped.

Follows repo conventions: ``REPO_ROOT``, ``main(argv=None)``, PyYAML + regex
only, reusing nothing that would couple it to the website/compendium build.
"""

import argparse
import datetime
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
ACTOR_MAP_FILE = REPO_ROOT / "config" / "foundry-actors.yaml"
DEFAULT_JSON_DIR = REPO_ROOT / "scratch" / "foundry-actors" / "actors-json"
OUTPUT_DIR = REPO_ROOT / "inbox" / "characters"

# Chasing Adventure stat keys, in sheet order (labels come from each stat's
# own ``label`` field, falling back to the upper-cased key).
STAT_KEYS = ["str", "dex", "int", "wis", "cha"]

# Move types every character carries by default — filtered out so the snapshot
# shows only what the player chose.
BASIC_MOVE_TYPES = {"adventure", "peripheral"}
# Move types rendered with full rules text (playbook picks, cross-class picks,
# and custom/organization moves which carry an empty type).
PRIMARY_MOVE_TYPES = {"class", ""}

_EMPHASIS = {"strong": "**", "b": "**", "em": "*", "i": "*"}


class _MarkdownParser(HTMLParser):
    """Convert Foundry ProseMirror HTML to Markdown.

    Emphasis is handled with a stack so nested ``<em><strong>…`` and the trailing
    whitespace ProseMirror tucks inside tags don't produce dangling ``*`` markers:
    inner text is stripped and the markers hug it, with surrounding spaces emitted
    outside the markers.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.stack = []  # [(tag, buffer), ...] for open emphasis spans

    def _emit(self, text):
        (self.stack[-1][1] if self.stack else self.out).append(text)

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in _EMPHASIS:
            self.stack.append((tag, []))
        elif tag == "br":
            self._emit("\n")
        elif tag == "hr":
            self._emit("\n\n---\n\n")
        elif tag == "li":
            self._emit("\n- ")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in _EMPHASIS:
            if any(t == tag for t, _ in self.stack):
                while self.stack:  # unwind to the matching tag (tolerate misnesting)
                    t, buf = self.stack.pop()
                    inner = "".join(buf)
                    stripped = inner.strip()
                    if stripped:
                        lead = inner[: len(inner) - len(inner.lstrip())]
                        trail = inner[len(inner.rstrip()):]
                        marker = _EMPHASIS[t]
                        self._emit(f"{lead}{marker}{stripped}{marker}{trail}")
                    else:
                        self._emit(inner)
                    if t == tag:
                        break
        elif tag == "p":
            self._emit("\n\n")
        elif tag in ("ul", "ol"):
            self._emit("\n")

    def handle_data(self, data):
        self._emit(data)

    def result(self):
        while self.stack:  # flush any unclosed emphasis spans as plain text
            _, buf = self.stack.pop()
            self._emit("".join(buf))
        return "".join(self.out)


def html_to_markdown(raw):
    """Best-effort HTML → Markdown for Foundry rich-text descriptions."""
    if not raw:
        return ""
    parser = _MarkdownParser()
    parser.feed(raw)
    s = parser.result()
    s = re.sub(r"(?m)[ \t]+$", "", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def _attr(sysd, key):
    """Read system.attributes.<key>.value (or None)."""
    return ((sysd.get("attributes", {}) or {}).get(key, {}) or {}).get("value")


def _safe_json(raw):
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return []


def _equipment_tags(raw):
    """Equipment tags are stored as a JSON string like '[{"value":"large"}]'."""
    if not raw:
        return []
    items = raw if isinstance(raw, list) else _safe_json(raw)
    tags = []
    for t in items or []:
        value = t.get("value") if isinstance(t, dict) else t
        if value:
            tags.append(str(value).strip())
    return tags


def extract_build(actor):
    """Pull the persistent Chasing Adventure build out of one unpacked actor."""
    sysd = actor.get("system", {}) or {}
    stats = sysd.get("stats", {}) or {}
    moves = []            # primary moves: name + description
    subsystem = {}        # moveType -> [name, ...] (favor/chase/follower/…)
    equipment = []
    for item in actor.get("items", []) or []:
        itype = item.get("type")
        isys = item.get("system", {}) or {}
        name = (item.get("name") or "").strip()
        if itype == "move":
            mtype = isys.get("moveType") or ""
            if mtype in BASIC_MOVE_TYPES:
                continue
            if mtype in PRIMARY_MOVE_TYPES:
                moves.append({"name": name, "description": html_to_markdown(isys.get("description", ""))})
            else:
                subsystem.setdefault(mtype, []).append(name)
        elif itype == "equipment":
            equipment.append({
                "name": name,
                "tags": _equipment_tags(isys.get("tags")),
                "description": html_to_markdown(isys.get("description", "")),
            })
    return {
        "name": actor.get("name", ""),
        "playbook": ((sysd.get("playbook") or {}).get("name") or "").strip(),
        "level": _attr(sysd, "level"),
        "xp": _attr(sysd, "xp"),
        "armor": _attr(sysd, "armor"),
        "drive": html_to_markdown(_attr(sysd, "drive") or ""),
        "background": html_to_markdown(_attr(sysd, "background") or ""),
        "stats": {k: (stats.get(k, {}) or {}) for k in STAT_KEYS},
        "moves": moves,
        "subsystem": subsystem,
        "equipment": equipment,
    }


def render_snapshot(build, slug, today):
    """Render one inbox/characters snapshot (frontmatter + readable build)."""
    fm = {
        "source": "foundry",
        "world": "pbta-test",
        "actor": build["name"],
        "pc_slug": slug,
        "generated": today,
    }
    lines = ["---", yaml.safe_dump(fm, sort_keys=False).strip(), "---", ""]
    lines.append(f"# {build['name']} — Foundry sheet snapshot")
    lines.append("")
    lines.append(
        "_Generated from the live Foundry sheet by `scripts/extract_characters.py`. "
        "Fold into the entry with `/incorporate-characters`._"
    )
    lines.append("")

    level = build["level"] if build["level"] is not None else "?"
    head = f"**Playbook:** {build['playbook']} — Level {level}" if build["playbook"] \
        else f"**Level:** {level}"
    if build["xp"] is not None:
        head += f" ({build['xp']} XP)"
    if build["armor"] is not None:
        head += f" · Armor {build['armor']}"
    lines.append(head)

    stat_parts = []
    for key in STAT_KEYS:
        stat = build["stats"].get(key) or {}
        if stat.get("value") is not None:
            label = (stat.get("label") or key.upper()).strip()
            stat_parts.append(f"{label} {stat['value']}")
    if stat_parts:
        lines.append(f"**Stats:** {', '.join(stat_parts)}")

    if build["drive"]:
        lines += ["", "## Drive", build["drive"]]
    if build["background"]:
        lines += ["", "## Background", build["background"]]

    if build["moves"]:
        lines += ["", "## Moves"]
        for move in build["moves"]:
            lines += ["", f"### {move['name']}"]
            if move["description"]:
                lines.append(move["description"])

    if build["subsystem"]:
        lines += ["", "## Subsystem moves"]
        for mtype in sorted(build["subsystem"]):
            lines.append(f"- **{mtype.capitalize()}:** {', '.join(build['subsystem'][mtype])}")

    if build["equipment"]:
        lines += ["", "## Equipment"]
        for eq in build["equipment"]:
            tags = f" — *{', '.join(eq['tags'])}*" if eq["tags"] else ""
            lines += ["", f"### {eq['name']}{tags}"]
            if eq["description"]:
                lines.append(eq["description"])

    return "\n".join(lines).rstrip() + "\n"


def load_actor_map():
    data = yaml.safe_load(ACTOR_MAP_FILE.read_text(encoding="utf-8")) or {}
    return {str(k): str(v) for k, v in data.items()}


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, default=DEFAULT_JSON_DIR,
                   help="dir of unpacked actor JSON (default: %(default)s)")
    p.add_argument("--output", type=Path, default=OUTPUT_DIR,
                   help="dir for snapshot files (default: %(default)s)")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if not args.input.exists():
        sys.exit(f"No actor JSON at {args.input}. Run scripts/pull_actors.sh first.")
    json_files = sorted(args.input.glob("*.json"))
    if not json_files:
        sys.exit(f"No *.json files in {args.input}. Run scripts/pull_actors.sh first.")

    actor_map = load_actor_map()
    args.output.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()

    written, unmapped = 0, 0
    for jf in json_files:
        actor = json.loads(jf.read_text(encoding="utf-8"))
        name = actor.get("name", "")
        slug = actor_map.get(name)
        if not slug:
            print(f"  ? actor {name!r} not in config/foundry-actors.yaml — skipped")
            unmapped += 1
            continue
        build = extract_build(actor)
        out_path = args.output / f"{slug}.md"
        out_path.write_text(render_snapshot(build, slug, today), encoding="utf-8")
        print(f"  + {out_path.relative_to(REPO_ROOT)}")
        written += 1

    print(f"\nWrote {written} snapshot(s) to {args.output.relative_to(REPO_ROOT)}/, "
          f"{unmapped} unmapped actor(s) skipped.")
    print("Next: run /incorporate-characters to fold them into kb/pcs/ entries.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

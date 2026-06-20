#!/usr/bin/env python3
"""Prepare a raw campaign transcript: map Discord speaker names to character
names and apply transcription corrections.

Accepts either of two raw input formats and auto-detects which it is:

1. Cleaned line format (output of download_transcript.py), one turn per line:
       [TIMESTAMP] SPEAKER: TEXT

2. Markdown export from the transcription service (raw/session-N.md), where
   each turn is a bolded speaker header followed by the spoken text:
       **Speaker Name** - 01:13:01 PM
       Spoken text, possibly spanning several lines.
   A `## Transcript` heading separates the body from the metadata header, and
   the recording date lives in a `**Date**: June 13, 2026 ...` header line.
   Markdown input is normalized into the cleaned line format before mapping.

Produces a prepared transcript with speaker names mapped to display names
(e.g. "Killjoy Keegan" → "GM") and common transcription errors corrected.
"""

import argparse
import datetime as _dt
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = REPO_ROOT / "config" / "speaker-map.yaml"

# Matches lines like: [1/10/2026 2:56 PM] SomeUser: Hello world
LINE_RE = re.compile(r"^(\[.+?\])\s+(.+?):\s+(.+)$")

# --- New markdown transcription-service format ----------------------------
# The `## Transcript` heading marks the boundary between the metadata header
# and the spoken turns.
MD_TRANSCRIPT_HEADER_RE = re.compile(r"^##\s+Transcript\s*$")
# A turn header: **Speaker Name** - 1:13:01 PM   (seconds optional)
MD_SPEAKER_RE = re.compile(r"^\*\*(.+?)\*\*\s+-\s+(\d{1,2}:\d{2}(?::\d{2})?\s*[AP]M)\s*$")
# The recording date in the metadata header: **Date**: June 13, 2026 at ...
MD_DATE_RE = re.compile(r"\*\*Date\*\*:\s*([A-Za-z]+\s+\d{1,2},\s*\d{4})")


def is_markdown_transcript(text):
    """Return True if text is the new markdown transcription-service export.

    Identified by a `## Transcript` heading plus at least one bolded
    `**Speaker** - TIME` turn header.
    """
    if not any(MD_TRANSCRIPT_HEADER_RE.match(line) for line in text.splitlines()):
        return False
    return any(MD_SPEAKER_RE.match(line.rstrip()) for line in text.splitlines())


def parse_markdown_date(text):
    """Extract the recording date as 'M/D/YYYY', or None if absent/unparseable."""
    m = MD_DATE_RE.search(text)
    if not m:
        return None
    try:
        d = _dt.datetime.strptime(m.group(1).replace(",", ""), "%B %d %Y")
    except ValueError:
        return None
    return f"{d.month}/{d.day}/{d.year}"


def markdown_to_cleaned_lines(text):
    """Convert the markdown transcript export into cleaned-format lines.

    Each spoken turn becomes a single '[DATE TIME] speaker: text' line so the
    rest of the pipeline (speaker mapping, corrections, manifest) is unchanged.
    Metadata header, presence/voice-event lines, and blank lines are dropped.
    """
    date_str = parse_markdown_date(text)
    lines = text.splitlines()

    # Skip everything up to and including the `## Transcript` heading.
    start = 0
    for i, line in enumerate(lines):
        if MD_TRANSCRIPT_HEADER_RE.match(line):
            start = i + 1
            break

    out = []
    i = start
    while i < len(lines):
        m = MD_SPEAKER_RE.match(lines[i].rstrip())
        if not m:
            # Presence lines, voice events, blanks, stray markdown — skip.
            i += 1
            continue
        speaker = m.group(1).strip()
        time_str = m.group(2).strip()
        i += 1
        # Collect the body until a blank line or the next turn header.
        body = []
        while i < len(lines) and lines[i].strip() and not MD_SPEAKER_RE.match(lines[i].rstrip()):
            body.append(lines[i].strip())
            i += 1
        spoken = " ".join(body).strip()
        if not spoken:
            continue
        timestamp = f"{date_str} {time_str}" if date_str else time_str
        out.append(f"[{timestamp}] {speaker}: {spoken}")
    return out


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Process a raw campaign transcript: map speakers and fix transcription errors.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='examples:\n'
               '  %(prog)s --input inbox/transcripts/raw/session-1.txt --session 1\n'
               '  %(prog)s --input raw.txt --output processed.txt --session 3\n',
    )
    parser.add_argument(
        "--input", type=str, required=True,
        help="Path to the raw transcript file.",
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Override output path (default: inbox/transcripts/prepared/session-{N}.txt).",
    )
    parser.add_argument(
        "--session", type=int, required=True,
        help="Session number (required). Used in output filename and to select the correct character for multi-character players.",
    )
    parser.add_argument(
        "--config", type=str, default=None,
        help=f"Path to speaker-map.yaml (default: {DEFAULT_CONFIG.relative_to(REPO_ROOT)}).",
    )
    return parser.parse_args(argv)


def load_config(config_path):
    """Load and return the speaker-map YAML config."""
    path = Path(config_path) if config_path else DEFAULT_CONFIG
    if not path.exists():
        print(f"Error: Config file not found: {path}", file=sys.stderr)
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_session_range(range_str):
    """Parse a session range string into (start, end) where end may be None (open-ended).

    Formats: "0-" (0 to infinity), "0-5" (0 to 5 inclusive), "3" (session 3 only).
    """
    range_str = str(range_str).strip()
    if "-" in range_str:
        parts = range_str.split("-", 1)
        start = int(parts[0])
        end = int(parts[1]) if parts[1] else None
        return start, end
    else:
        n = int(range_str)
        return n, n


def session_in_range(session_num, range_str):
    """Check if a session number falls within a range string."""
    start, end = parse_session_range(range_str)
    if session_num < start:
        return False
    if end is not None and session_num > end:
        return False
    return True


def build_speaker_map(config, session_num=None):
    """Build a {lowercase_discord_name: display_name} dict from config.

    For players with characters, uses the character's display name.
    If session_num is provided, picks the character active in that session.
    Otherwise, uses the first active character.
    """
    speaker_map = {}
    players = config.get("players", {})

    for player_key, player in players.items():
        discord_names = player.get("discord_names", [])
        display = None

        if player.get("role") == "gm":
            display = player.get("display", player_key.capitalize())
        else:
            characters = player.get("characters", [])
            for char in characters:
                if session_num is not None:
                    sessions = char.get("sessions", "0-")
                    if session_in_range(session_num, sessions) and char.get("active", True):
                        display = char.get("display", char.get("name"))
                        break
                else:
                    # No session specified — use first active character
                    if char.get("active", True):
                        display = char.get("display", char.get("name"))
                        break

        if display:
            for name in discord_names:
                speaker_map[name.lower()] = display

    return speaker_map


def map_speaker(speaker, speaker_map):
    """Look up a speaker name, return (display_name, was_mapped)."""
    key = speaker.lower()
    if key in speaker_map:
        return speaker_map[key], True
    return speaker, False


def apply_corrections(text, corrections):
    """Apply case-insensitive regex replacements to text."""
    for entry in corrections:
        match = entry.get("match", "")
        replace = entry.get("replace", "")
        if match:
            text = re.sub(re.escape(match), replace, text, flags=re.IGNORECASE)
    return text


def determine_output_path(args):
    """Determine output path using session number."""
    if args.output:
        return Path(args.output)

    return REPO_ROOT / "inbox" / "transcripts" / "prepared" / f"session-{args.session}.txt"


def prepare_transcript(lines, speaker_map, corrections):
    """Prepare transcript lines: map speakers and apply corrections.

    Returns (output_lines, speaker_counts, corrections_count, unmapped_speakers).
    """
    output_lines = []
    speaker_counts = defaultdict(int)
    corrections_count = 0
    unmapped_speakers = set()

    for line in lines:
        m = LINE_RE.match(line)
        if not m:
            # Pass through non-matching lines unchanged
            output_lines.append(line)
            continue

        timestamp = m.group(1)
        speaker = m.group(2)
        text = m.group(3)

        # Map speaker name
        display_name, was_mapped = map_speaker(speaker, speaker_map)
        if not was_mapped:
            unmapped_speakers.add(speaker)
        speaker_counts[display_name] += 1

        # Apply corrections to text portion only
        corrected_text = apply_corrections(text, corrections)
        if corrected_text != text:
            corrections_count += 1

        output_lines.append(f"{timestamp} {display_name}: {corrected_text}")

    return output_lines, speaker_counts, corrections_count, unmapped_speakers


def main(argv=None):
    args = parse_args(argv)

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    config = load_config(args.config)
    speaker_map = build_speaker_map(config, args.session)
    corrections = config.get("transcription_corrections", [])

    raw_text = input_path.read_text(encoding="utf-8")
    if is_markdown_transcript(raw_text):
        lines = markdown_to_cleaned_lines(raw_text)
        print(f"Detected markdown transcript format: {len(lines)} turns parsed.")
    else:
        lines = raw_text.splitlines()

    output_lines, speaker_counts, corrections_count, unmapped = prepare_transcript(
        lines, speaker_map, corrections,
    )

    output_path = determine_output_path(args)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(output_lines) + "\n" if output_lines else "", encoding="utf-8")

    # Summary output
    print(f"Prepared transcript: {input_path}")
    print(f"  Output: {output_path}")
    print(f"  Lines processed: {len(lines)}")
    if speaker_counts:
        print("  Speakers found:")
        for name in sorted(speaker_counts):
            print(f"    {name}: {speaker_counts[name]} lines")
    print(f"  Corrections applied: {corrections_count}")
    if unmapped:
        print()
        print("  WARNING: Unmapped speakers (kept original name):")
        for name in sorted(unmapped):
            print(f"    - {name}")

    return str(output_path)


if __name__ == "__main__":
    main()

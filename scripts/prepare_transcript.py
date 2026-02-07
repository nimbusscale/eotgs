#!/usr/bin/env python3
"""Prepare a raw Grimwild transcript: map Discord speaker names to character
names and apply transcription corrections.

Reads a raw transcript (output of download_transcript.py) where each line is:
    [TIMESTAMP] SPEAKER: TEXT

Produces a prepared transcript with speaker names mapped to display names
(e.g. "Killjoy Keegan" → "GM") and common transcription errors corrected.
"""

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = REPO_ROOT / "config" / "speaker-map.yaml"

# Matches lines like: [1/10/2026 2:56 PM] SomeUser: Hello world
LINE_RE = re.compile(r"^(\[.+?\])\s+(.+?):\s+(.+)$")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Process a raw Grimwild transcript: map speakers and fix transcription errors.",
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

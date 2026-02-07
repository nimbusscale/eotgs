#!/usr/bin/env python3
"""Download and clean a raw Discord transcript from the Grimwild voice channel.

Uses DiscordChatExporter.Cli to download, then strips bot noise and
deduplicates progressive transcription updates from SeaVoice. Outputs a
clean transcript with original Discord speaker names (no name mapping or
transcription corrections — those are handled by prepare_transcript.py).
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

CHANNEL_ID = "1391520853824508058"
BOT_TOKEN_ENV = "DISCORD_CHAT_EXPORTER_BOT_TOKEN"
CLI_CMD = "DiscordChatExporter.Cli"

# Regex for message header: [M/D/YYYY H:MM AM/PM] Author#Discriminator
HEADER_RE = re.compile(r"^\[(.+?)\]\s+(.+)$")
# Regex for transcript content: **Speaker**:  text
TRANSCRIPT_RE = re.compile(r"^\*\*(.+?)\*\*:\s+(.+)$")
# Regex for channel name from file header
CHANNEL_RE = re.compile(r"^Channel:\s+.+/\s*(.+)$")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Download and clean a Grimwild voice channel transcript.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='examples:\n'
               '  %(prog)s --after "2026-01-10 14:00" --before "2026-01-10 18:00"\n'
               '  %(prog)s --after "2026-01-10 14:00"\n'
               '  %(prog)s --input transcript.txt\n',
    )
    parser.add_argument(
        "--after", type=str, default=None, metavar="DATETIME",
        help='Start datetime as "YYYY-MM-DD HH:MM" (default: 6 hours ago). '
             'Example: "2026-01-10 14:00". Ignored if --input provided.',
    )
    parser.add_argument(
        "--before", type=str, default=None, metavar="DATETIME",
        help='End datetime as "YYYY-MM-DD HH:MM" (default: now). '
             'Example: "2026-01-10 18:00". Ignored if --input provided.',
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Override output path (default: inbox/transcripts/raw/session-{N}.txt).",
    )
    parser.add_argument(
        "--input", type=str, default=None,
        help="Path to an already-downloaded transcript. Skips the download step.",
    )
    parser.add_argument(
        "--session", type=int, required=True,
        help="Session number (required). Used in output filename.",
    )
    return parser.parse_args(argv)


def download_transcript(after: str, before: str) -> str:
    """Run DiscordChatExporter.Cli and return path to downloaded file."""
    token = os.environ.get(BOT_TOKEN_ENV)
    if not token:
        print(f"Error: {BOT_TOKEN_ENV} environment variable not set.", file=sys.stderr)
        sys.exit(1)

    tmp = tempfile.NamedTemporaryFile(suffix=".txt", delete=False, prefix="grimwild_")
    tmp.close()

    cmd = [
        CLI_CMD, "export",
        "--token", token,
        "--channel", CHANNEL_ID,
        "--format", "PlainText",
        "--after", after,
        "--before", before,
        "--output", tmp.name,
    ]

    print(f"Downloading transcript ({after} to {before})...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"DiscordChatExporter.Cli failed (exit {result.returncode}):", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        if result.stdout:
            print(result.stdout, file=sys.stderr)
        sys.exit(1)

    print(f"Downloaded to {tmp.name}")
    return tmp.name


def parse_messages(text: str):
    """Parse raw transcript text into message blocks.

    Yields dicts with keys: timestamp, author, content (full block text),
    and for transcript lines: speaker, text.
    """
    lines = text.split("\n")
    channel_name = None

    # Extract channel name from header
    for line in lines:
        m = CHANNEL_RE.match(line)
        if m:
            channel_name = m.group(1).strip()
            break

    # Parse message blocks
    i = 0
    while i < len(lines):
        header_match = HEADER_RE.match(lines[i])
        if not header_match:
            i += 1
            continue

        timestamp = header_match.group(1)
        author = header_match.group(2)

        # Collect content lines until next header or end
        i += 1
        content_lines = []
        while i < len(lines):
            if HEADER_RE.match(lines[i]):
                break
            content_lines.append(lines[i])
            i += 1

        content = "\n".join(content_lines).strip()
        msg = {
            "timestamp": timestamp,
            "author": author,
            "content": content,
            "speaker": None,
            "text": None,
        }

        # Try to extract speaker/text from transcript line
        for cl in content_lines:
            cl = cl.strip()
            tm = TRANSCRIPT_RE.match(cl)
            if tm:
                msg["speaker"] = tm.group(1)
                msg["text"] = tm.group(2)
                break

        yield channel_name, msg


def clean_transcript(raw_text: str):
    """Parse and clean the transcript, returning (channel_name, lines).

    Each line is a dict with timestamp, speaker, text.
    """
    entries = []
    channel_name = None

    for ch_name, msg in parse_messages(raw_text):
        if ch_name and not channel_name:
            channel_name = ch_name

        # Skip non-SeaVoice authors
        if not msg["author"].startswith("SeaVoice"):
            continue

        # Skip embed/bot messages
        if "{Embed}" in msg["content"]:
            continue

        # Skip if no transcript content
        if not msg["speaker"] or not msg["text"]:
            continue

        entries.append(msg)

    # Deduplicate progressive transcriptions
    deduped = []
    for entry in entries:
        if deduped:
            prev = deduped[-1]
            if (prev["speaker"] == entry["speaker"]
                    and entry["text"].startswith(prev["text"])):
                # Replace previous with longer version
                deduped[-1] = entry
                continue
        deduped.append(entry)

    return channel_name, deduped


def format_output(entries):
    """Format cleaned entries into output text."""
    lines = []
    for e in entries:
        lines.append(f"[{e['timestamp']}] {e['speaker']}: {e['text']}")
    return "\n".join(lines) + "\n" if lines else ""


def determine_output_path(args):
    """Determine the output file path."""
    if args.output:
        return Path(args.output)

    repo_root = Path(__file__).resolve().parent.parent
    return repo_root / "inbox" / "transcripts" / "raw" / f"session-{args.session}.txt"


def main(argv=None):
    args = parse_args(argv)

    if args.input:
        input_path = args.input
        after_str = args.after
    else:
        now = datetime.now()
        after_str = args.after or (now - timedelta(hours=6)).strftime("%Y-%m-%d %H:%M")
        before_str = args.before or now.strftime("%Y-%m-%d %H:%M")
        input_path = download_transcript(after_str, before_str)

    raw_text = Path(input_path).read_text(encoding="utf-8")
    channel_name, entries = clean_transcript(raw_text)

    output_path = determine_output_path(args)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_text = format_output(entries)
    output_path.write_text(output_text, encoding="utf-8")

    print(f"Wrote {len(entries)} transcript lines to {output_path}")

    # Clean up temp file if we downloaded
    if not args.input and os.path.exists(input_path):
        os.unlink(input_path)

    return str(output_path)


if __name__ == "__main__":
    main()

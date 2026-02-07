#!/usr/bin/env python3
"""Combined transcript ingest: download from Discord and prepare in one step.

Wrapper around download_transcript.py and prepare_transcript.py. Runs both
steps by default, or a single step with --download-only / --prepare-only.
"""

import argparse
import sys
from pathlib import Path

# Allow imports from the scripts directory
sys.path.insert(0, str(Path(__file__).resolve().parent))

from download_transcript import main as download_main
from prepare_transcript import main as prepare_main

REPO_ROOT = Path(__file__).resolve().parent.parent


def parse_args():
    parser = argparse.ArgumentParser(
        description="Download and prepare a Grimwild voice channel transcript.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='examples:\n'
               '  %(prog)s --session 3\n'
               '  %(prog)s --session 3 --after "2026-01-10 14:00"\n'
               '  %(prog)s --session 3 --prepare-only --input inbox/transcripts/raw/session-3.txt\n'
               '  %(prog)s --session 3 --download-only\n',
    )
    parser.add_argument(
        "--session", type=int, required=True,
        help="Session number (required).",
    )

    # Step selection
    step_group = parser.add_mutually_exclusive_group()
    step_group.add_argument(
        "--download-only", action="store_true",
        help="Run only the download step.",
    )
    step_group.add_argument(
        "--prepare-only", action="store_true",
        help="Run only the prepare step.",
    )

    # Download options
    parser.add_argument(
        "--after", type=str, default=None, metavar="DATETIME",
        help='Start datetime for Discord export (default: 6h ago). '
             'Example: "2026-01-10 14:00".',
    )
    parser.add_argument(
        "--before", type=str, default=None, metavar="DATETIME",
        help='End datetime for Discord export (default: now). '
             'Example: "2026-01-10 18:00".',
    )
    parser.add_argument(
        "--input", type=str, default=None, metavar="PATH",
        help="Pre-downloaded transcript file (skips Discord download).",
    )

    # Prepare options
    parser.add_argument(
        "--config", type=str, default=None, metavar="PATH",
        help="Path to speaker-map.yaml (default: config/speaker-map.yaml).",
    )

    return parser.parse_args()


def default_raw_path(session):
    """Return the default raw transcript path for a session."""
    return str(REPO_ROOT / "inbox" / "transcripts" / "raw" / f"session-{session}.txt")


def main():
    args = parse_args()

    run_download = not args.prepare_only
    run_prepare = not args.download_only

    # Determine raw transcript path
    if run_download:
        download_argv = ["--session", str(args.session)]
        if args.after:
            download_argv += ["--after", args.after]
        if args.before:
            download_argv += ["--before", args.before]
        if args.input:
            download_argv += ["--input", args.input]
        raw_path = download_main(download_argv)
    else:
        raw_path = args.input or default_raw_path(args.session)

    if run_prepare:
        prepare_argv = ["--input", raw_path, "--session", str(args.session)]
        if args.config:
            prepare_argv += ["--config", args.config]
        prepare_main(prepare_argv)


if __name__ == "__main__":
    main()

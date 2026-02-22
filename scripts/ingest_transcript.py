#!/usr/bin/env python3
"""Combined transcript ingest: download, prepare, and chunk in one step.

Wrapper around download_transcript.py, prepare_transcript.py, and
chunk_transcript.py. Runs all three steps by default, or a single step
with --download-only / --prepare-only.
"""

import argparse
import sys
from pathlib import Path

# Allow imports from the scripts directory
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sync_kb_aliases import main as sync_aliases_main
from download_transcript import main as download_main
from prepare_transcript import main as prepare_main
from chunk_transcript import main as chunk_main

REPO_ROOT = Path(__file__).resolve().parent.parent


def parse_args():
    parser = argparse.ArgumentParser(
        description="Download, prepare, and chunk a Grimwild voice channel transcript.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='examples:\n'
               '  %(prog)s --session 3\n'
               '  %(prog)s --session 3 --after "2026-01-10 14:00"\n'
               '  %(prog)s --session 3 --prepare-only --input inbox/transcripts/raw/session-3.txt\n'
               '  %(prog)s --session 3 --download-only\n'
               '  %(prog)s --session 3 --skip-chunk\n',
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
        help="Run only the prepare step (no chunking).",
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

    # Chunk options
    parser.add_argument(
        "--skip-chunk", action="store_true",
        help="Skip the chunking step.",
    )
    parser.add_argument(
        "--chunk-size", type=int, default=800,
        help="Lines per chunk (default: 800).",
    )
    parser.add_argument(
        "--overlap", type=int, default=50,
        help="Lines of overlap between chunks (default: 50).",
    )

    return parser.parse_args()


def default_raw_path(session):
    """Return the default raw transcript path for a session."""
    return str(REPO_ROOT / "inbox" / "transcripts" / "raw" / f"session-{session}.txt")


def default_prepared_path(session):
    """Return the default prepared transcript path for a session."""
    return str(REPO_ROOT / "inbox" / "transcripts" / "prepared" / f"session-{session}.txt")


def main():
    args = parse_args()

    # Sync KB sub-entity aliases before anything else
    sync_aliases_main(argv=[])

    run_download = not args.prepare_only
    run_prepare = not args.download_only
    run_chunk = not args.download_only and not args.prepare_only and not args.skip_chunk

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
        prepared_path = prepare_main(prepare_argv)
    else:
        prepared_path = default_prepared_path(args.session)

    if run_chunk:
        chunk_argv = [
            "--session", str(args.session),
            "--input", prepared_path,
            "--chunk-size", str(args.chunk_size),
            "--overlap", str(args.overlap),
        ]
        chunk_main(chunk_argv)


if __name__ == "__main__":
    main()

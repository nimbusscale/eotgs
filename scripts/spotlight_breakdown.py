#!/usr/bin/env python3
"""Compute objective talk-time per speaker from a prepared session transcript.

The prepared transcripts (inbox/transcripts/prepared/session-N.txt) carry a
per-line timestamp:

    [6/27/2026 01:43:11 PM] Garland: I don't share it with anybody...

This script parses those timestamps and attributes the elapsed time between
each line and the next to the line's speaker. It produces an OBJECTIVE baseline
(who held the mic, for how long, and where the long gaps are) that the
/review-session command pairs with a semantic spotlight read of the transcript.

It deliberately does NOT try to judge in-game vs out-of-game or which PC is in
the narrative spotlight -- that requires reading the fiction, which is the LLM's
job. This is just the clock.

Usage:
    python3 scripts/spotlight_breakdown.py --session 8
    python3 scripts/spotlight_breakdown.py --input path/to/prepared.txt
    python3 scripts/spotlight_breakdown.py --session 8 --json

Notes:
- Gaps longer than --gap-cap seconds (default 90) are treated as breaks/dead air
  and bucketed separately rather than credited to whoever spoke last, so a single
  word before a ten-minute break does not inflate that speaker's share.
"""

import argparse
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The transcripts use three timestamp formats across the campaign's history:
#   1. Dated, with seconds  (S7-8):  [6/27/2026 01:43:11 PM] Speaker: ...
#   2. Dated, minute-only   (S1-5):  [2/21/2026 2:07 PM] Speaker: ...
#   3. Elapsed, no date     (S6):    [34:54] or [01:29:19] Speaker: ...
# We normalize all three to a comparable datetime so the same diff math works.

DATED_RE = re.compile(
    r"^\[(?P<date>\d{1,2}/\d{1,2}/\d{4})\s+(?P<time>\d{1,2}:\d{2}(?::\d{2})?)\s+(?P<ampm>[AP]M)\]\s+"
    r"(?P<speaker>[^:\]]+?):\s?(?P<text>.*)$"
)
ELAPSED_RE = re.compile(
    r"^\[(?P<elapsed>\d{1,2}:\d{2}(?::\d{2})?)\]\s+"
    r"(?P<speaker>[^:\]]+?):\s?(?P<text>.*)$"
)

# Synthetic epoch for elapsed-format transcripts (only diffs matter).
EPOCH = datetime(2000, 1, 1)


def parse_dated(date: str, time: str, ampm: str):
    """Parse a dated timestamp. Returns (datetime, has_seconds)."""
    has_seconds = time.count(":") == 2
    fmt = "%m/%d/%Y %I:%M:%S %p" if has_seconds else "%m/%d/%Y %I:%M %p"
    return datetime.strptime(f"{date} {time} {ampm}", fmt), has_seconds


def parse_elapsed(elapsed: str) -> datetime:
    """Parse an elapsed MM:SS or H:MM:SS offset into a synthetic datetime."""
    parts = [int(p) for p in elapsed.split(":")]
    if len(parts) == 2:
        minutes, seconds = parts
        total = minutes * 60 + seconds
    else:
        hours, minutes, seconds = parts
        total = hours * 3600 + minutes * 60 + seconds
    return EPOCH + timedelta(seconds=total)


def parse_transcript(path: Path):
    """Return (events, resolution, is_elapsed).

    events is a list of (datetime, speaker, text).
    resolution is "second" if any line carried seconds, else "minute" (the older
    minute-only transcripts, where sub-minute gaps are invisible and per-line
    attribution is coarse).
    is_elapsed is True for the elapsed/relative format (no wall-clock date).
    """
    events = []
    has_any_seconds = False
    is_elapsed = False
    # Elapsed transcripts can be stitched from several recordings whose clocks each
    # restart near zero. Track a running offset so the synthetic clock stays
    # monotonic across those segment boundaries (with a tiny seam gap).
    offset = 0.0
    prev_raw = None
    segments = 1
    SEAM = 2.0
    for raw in path.read_text(encoding="utf-8").splitlines():
        m = DATED_RE.match(raw)
        if m:
            try:
                ts, has_seconds = parse_dated(m["date"], m["time"], m["ampm"])
            except ValueError:
                continue
            has_any_seconds = has_any_seconds or has_seconds
            events.append((ts, m["speaker"].strip(), m["text"].strip()))
            continue
        m = ELAPSED_RE.match(raw)
        if m:
            cur_raw = (parse_elapsed(m["elapsed"]) - EPOCH).total_seconds()
            if prev_raw is not None and cur_raw < prev_raw:
                # new segment: continue the clock just after the previous one ended
                offset += prev_raw + SEAM - cur_raw
                segments += 1
            prev_raw = cur_raw
            ts = EPOCH + timedelta(seconds=offset + cur_raw)
            has_any_seconds = True  # elapsed format always carries seconds
            is_elapsed = True
            events.append((ts, m["speaker"].strip(), m["text"].strip()))
    resolution = "second" if has_any_seconds else "minute"
    return events, resolution, is_elapsed, segments if is_elapsed else 1


def fmt_hms(seconds: float) -> str:
    seconds = int(round(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h{m:02d}m{s:02d}s"
    return f"{m}m{s:02d}s"


def analyze(events, gap_cap: int, resolution: str = "second", is_elapsed: bool = False,
            segments: int = 1):
    if len(events) < 2:
        raise SystemExit("Not enough timestamped lines to analyze.")

    talk = {}        # speaker -> attributed seconds
    line_counts = {}  # speaker -> number of lines
    big_gaps = []     # (start_dt, gap_seconds, speaker_before, speaker_after)
    idle_seconds = 0.0

    for i in range(len(events) - 1):
        ts, speaker, _ = events[i]
        nxt_ts, nxt_speaker, _ = events[i + 1]
        gap = (nxt_ts - ts).total_seconds()
        line_counts[speaker] = line_counts.get(speaker, 0) + 1

        if gap < 0:
            gap = 0  # clock glitches / out-of-order lines
        if gap > gap_cap:
            idle_seconds += gap
            big_gaps.append((ts, gap, speaker, nxt_speaker))
        else:
            talk[speaker] = talk.get(speaker, 0.0) + gap

    # last line gets a nominal couple seconds so it is counted at all
    last_speaker = events[-1][1]
    line_counts[last_speaker] = line_counts.get(last_speaker, 0) + 1
    talk[last_speaker] = talk.get(last_speaker, 0.0) + 2

    wall_clock = (events[-1][0] - events[0][0]).total_seconds()
    attributed = sum(talk.values())

    speakers = []
    for name, secs in sorted(talk.items(), key=lambda kv: kv[1], reverse=True):
        speakers.append({
            "speaker": name,
            "seconds": round(secs, 1),
            "hms": fmt_hms(secs),
            "pct_of_attributed": round(100 * secs / attributed, 1) if attributed else 0.0,
            "lines": line_counts.get(name, 0),
        })

    gm_seconds = sum(s["seconds"] for s in speakers if s["speaker"].lower() == "gm")
    player_seconds = attributed - gm_seconds

    big_gaps.sort(key=lambda g: g[1], reverse=True)
    top_gaps = [{
        "at": g[0].strftime("%I:%M:%S %p"),
        "gap": fmt_hms(g[1]),
        "gap_seconds": round(g[1], 1),
        "before": g[2],
        "after": g[3],
    } for g in big_gaps[:10]]

    if is_elapsed:
        start_label, end_label = "0:00 (elapsed)", fmt_hms(wall_clock) + " (elapsed)"
    else:
        start_label = events[0][0].strftime("%Y-%m-%d %I:%M:%S %p")
        end_label = events[-1][0].strftime("%Y-%m-%d %I:%M:%S %p")

    return {
        "resolution": resolution,
        "is_elapsed": is_elapsed,
        "segments": segments,
        "session_start": start_label,
        "session_end": end_label,
        "wall_clock_seconds": round(wall_clock, 1),
        "wall_clock_hms": fmt_hms(wall_clock),
        "attributed_talk_seconds": round(attributed, 1),
        "attributed_talk_hms": fmt_hms(attributed),
        "idle_break_seconds": round(idle_seconds, 1),
        "idle_break_hms": fmt_hms(idle_seconds),
        "gap_cap_seconds": gap_cap,
        "gm_seconds": round(gm_seconds, 1),
        "gm_pct_of_attributed": round(100 * gm_seconds / attributed, 1) if attributed else 0.0,
        "player_seconds": round(player_seconds, 1),
        "player_pct_of_attributed": round(100 * player_seconds / attributed, 1) if attributed else 0.0,
        "speakers": speakers,
        "longest_gaps": top_gaps,
    }


def render_markdown(data: dict) -> str:
    out = []
    out.append("## Objective talk-time (clock, not narrative spotlight)\n")
    out.append(
        f"- Session length (wall clock): **{data['wall_clock_hms']}** "
        f"({data['session_start']} → {data['session_end']})"
    )
    out.append(
        f"- Active talk attributed: **{data['attributed_talk_hms']}**  |  "
        f"Idle / breaks (gaps > {data['gap_cap_seconds']}s): **{data['idle_break_hms']}**"
    )
    out.append(
        f"- GM mic time: **{data['gm_pct_of_attributed']}%** of active talk "
        f"({fmt_hms(data['gm_seconds'])})  |  "
        f"Players combined: **{data['player_pct_of_attributed']}%** ({fmt_hms(data['player_seconds'])})\n"
    )
    out.append("| Speaker | Talk time | % of active talk | Lines |")
    out.append("| --- | --- | --- | --- |")
    for s in data["speakers"]:
        out.append(f"| {s['speaker']} | {s['hms']} | {s['pct_of_attributed']}% | {s['lines']} |")
    if data["longest_gaps"]:
        out.append("\n_Longest gaps (likely breaks/dead air; cross-check against the fiction):_")
        for g in data["longest_gaps"][:5]:
            out.append(f"- {g['gap']} at {g['at']} ({g['before']} → {g['after']})")
    out.append(
        "\n> This is raw mic time per speaker, not spotlight. The GM naturally tops it "
        "(narration, every NPC). Use it as a floor under the semantic spotlight read, and "
        "to separate active play from breaks — not as the spotlight breakdown itself."
    )
    if data.get("resolution") == "minute":
        out.append(
            "> ⚠️ This transcript has **minute-resolution** timestamps (no seconds), so "
            "sub-minute gaps read as zero and per-speaker attribution is coarser than "
            "usual. Treat the percentages as approximate."
        )
    if data.get("segments", 1) > 1:
        out.append(
            f"> ⚠️ This transcript was stitched from **{data['segments']} recording "
            "segments** (the elapsed clock restarts); segment boundaries were bridged to "
            "keep the clock monotonic, but the wall-clock total is approximate."
        )
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--session", type=int, help="Session number (reads inbox/transcripts/prepared/session-N.txt)")
    g.add_argument("--input", type=str, help="Explicit path to a prepared transcript")
    ap.add_argument("--gap-cap", type=int, default=90,
                    help="Gaps longer than this (seconds) count as break/idle, not talk (default 90)")
    ap.add_argument("--json", action="store_true", help="Emit JSON only")
    args = ap.parse_args()

    if args.session is not None:
        path = ROOT / "inbox" / "transcripts" / "prepared" / f"session-{args.session}.txt"
    else:
        path = Path(args.input)
    if not path.exists():
        sys.exit(f"Prepared transcript not found: {path}")

    events, resolution, is_elapsed, segments = parse_transcript(path)
    data = analyze(events, args.gap_cap, resolution, is_elapsed, segments)
    data["source"] = str(path)

    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print(render_markdown(data))
        print("\n<!-- JSON -->")
        print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()

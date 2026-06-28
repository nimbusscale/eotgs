---
# Source of truth for identity/images. config/*.yaml are GENERATED from these
# blocks by scripts/build_index.py — do not hand-edit the generated files.
id: session-[NUMBER]
type: session
name: 'Session [NUMBER]: [TITLE]'
arc: [arc-slug]   # the arc directory this session lives in (kb/sessions/<arc>/)
date: [YYYY-MM-DD]
# images:          # optional; mirrors a config/image-map.yaml entry. Gallery
#                  # items take `subjects: [slug, ...]` so guests (NPCs/locations
#                  # without their own image) are discoverable as references.
# transcript: inbox/transcripts/prepared/session-[NUMBER].txt
#                  # optional, SOURCE-ONLY (excluded from all exports). The prepared
#                  # transcript that scene_sources line ranges point into.
# scene_sources:   # optional, SOURCE-ONLY (excluded from all exports). Labelled
#                  # spans into `transcript` so illustrate-session can read the
#                  # narrated detail behind each beat. Each entry: a short `beat`
#                  # label + a `lines: "start-end"` range.
#   - beat: "memory-stones in the Hall of Deep Memory"
#     lines: "1048-1206"
---
# Session [NUMBER]: [TITLE]

**Date Played:** [DATE]
**In-Game Timeline:** [IF TRACKED]

## Recap-Teaser
> [The teaser read at session start]

## Summary
[2-3 paragraph narrative of what happened]

## Major Events
- [Event 1]
- [Event 2]

## New Questions & Hooks
- [Question or hook introduced]

## Questions Answered / Arcs Advanced
- [Resolution or progress]

## Notable NPCs Introduced
- [[NPC Name]] - [Brief description]

## Notable Locations Visited
- [[Location Name]]

## Notable Quotes
> [Memorable lines]

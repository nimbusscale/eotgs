# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Echoes of the Godstorm is a campaign knowledge base system for managing a TTRPG campaign. It processes Discord voice channel transcripts into a structured markdown knowledge base optimized for Claude Projects. The workflow is semi-automated with human review via git diff before committing.

Summary of the current campaign can be found at @exports/campaign-index.md

## Common Commands

### Transcript Processing Pipeline

```bash
# 1. Download, prepare, and build the extraction manifest
python scripts/ingest_transcript.py --session N

# Individual steps (for troubleshooting):
#   python scripts/download_transcript.py --session N
#   python scripts/prepare_transcript.py --input inbox/transcripts/raw/session-N.txt --session N
#   python scripts/build_manifest.py --session N --input inbox/transcripts/prepared/session-N.txt

# 2. Extract structured data (use Claude Code slash command)
/extract-session

# 3. Incorporate into knowledge base (use Claude Code slash command)
/incorporate-session

# 4. Export for Claude Projects (use Claude Code slash command)
/export-kb
```

### Claude Code Slash Commands

- `/extract-session` - Filter non-game content from prepared transcripts, output structured YAML
- `/incorporate-session` - Process extracted YAML into KB files, create/update entities
- `/incorporate-notes` - Incorporate planning notes from Claude Mobile sessions
- `/export-kb` - Generate consolidated export files for Claude Project Knowledge, then build and deploy the website and the Foundry compendium
- `/export-foundry` - Mirror the KB into the `grimwild-kb` Foundry VTT compendium and deploy it (also run as part of `/export-kb`)

## Architecture

### Directory Structure

- `kb/` - Main knowledge base (sessions/, pcs/, npcs/, locations/, items/, factions/, story-arcs/, world/)
- `gm-notes/` - Private GM notes (excluded from player-visible exports)
- `inbox/transcripts/` - Processing pipeline: raw/ → prepared/ → extracted/ → processed/ (manifest/ holds transient extraction context)
- `inbox/notes/` - Planning notes awaiting incorporation
- `config/` - speaker-map.yaml (Discord→character mapping); entity-aliases.yaml, image-map.yaml, subject-index.yaml (GENERATED from kb frontmatter — see below)
- `exports/` - Generated files for Claude Projects
- `templates/` - Markdown templates for each entity type
- `knowledge/` - Chasing Adventure game system reference material
- `review/` - Conflicts and questions flagged for human review
- `site/` - Quartz static site generator (content/ and public/ are gitignored, built by `/publish-kb`)

### Key Configuration Files

- `config/speaker-map.yaml` - Maps Discord usernames to player/character names, contains transcription corrections (hand-maintained; not part of the frontmatter pipeline)
- `config/entity-aliases.yaml` - **Generated.** Maps entity name variants to canonical entity ids for wiki-link resolution
- `config/image-map.yaml` - **Generated.** Maps `subdir/id` (sessions: `sessions/<arc>/<id>`) → hero/gallery/library images
- `config/subject-index.yaml` - **Generated.** Maps entity slug → image files that depict it (cross-map reference discovery)

### Frontmatter is the single source of truth

Each `kb/**/*.md` file begins with a `---` YAML frontmatter block that owns the
entity's identity, hierarchy, and image associations:

- `id` (stable; defaults to the filename slug), `type` (pc|npc|location|item|faction|world|session),
  `name` (defaults to the H1), `aliases` (list), `part_of` (parent id, optional),
  `images` (`hero`/`gallery`/`library`), `contains` (page-less sub-entity records:
  `id` + `name` + optional `aliases`, each mirrored by a `## [[Name]]` body section),
  plus `status` (PCs) and `arc`+`date` (sessions).
- `config/entity-aliases.yaml`, `config/image-map.yaml`, and `config/subject-index.yaml`
  are **generated** from these blocks by `scripts/build_index.py` — **do not hand-edit
  them.** Edit the owning entity's frontmatter, then run `python3 scripts/build_index.py`.
- `python3 scripts/build_index.py --check` is the integrity gate (generated == committed);
  it should pass cleanly on `main`. `ingest_transcript.py` regenerates the maps automatically.
- `scripts/sync_kb_aliases.py` is a deprecated shim that now delegates to `build_index.py`.

## Conventions

### Markdown Formatting

- **One sentence per line** for all narrative prose (enables cleaner git diffs)
- **Wiki-style links**: Use `[[Entity Name]]` for cross-references, resolved via entity-aliases.yaml
- **Narrative voice**: All story content reads like fiction—never reference "the session", "the GM", or game mechanics meta

### Filename Slugification

Lowercase, hyphens for spaces, drop leading articles, remove punctuation:
- "The Ashen Vale" → `ashen-vale.md`
- "Sir Roderic Lightbearer" → `sir-roderic-lightbearer.md`

### Entity Types

PCs go in `kb/pcs/`, NPCs in `kb/npcs/`. Distinguish using `config/speaker-map.yaml` which lists all player characters.

## Workflow Principles

1. **Semi-automated with human review**: Claude proposes changes, user reviews via `git diff` before committing
2. **Context efficiency**: List KB filenames rather than reading all content; read only when needed
3. **Conflict handling**: Flag ambiguous updates in `review/pending-changes.md` for human decision
4. **Private content routing**: GM-only observations go to `gm-notes/`, not `kb/`

## Development Reference

Full specifications, templates, and development tasks are documented in `dev/PROJECT.md`.

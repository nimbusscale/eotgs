# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Grimwild KB is a campaign knowledge base system for managing a TTRPG campaign. It processes Discord voice channel transcripts into a structured markdown knowledge base optimized for Claude Projects. The workflow is semi-automated with human review via git diff before committing.

Summary of the current campaign can be found at @exports/campaign-index.md

## Common Commands

### Transcript Processing Pipeline

```bash
# 1. Download, prepare, and chunk transcript
python scripts/ingest_transcript.py --session N

# Individual steps (for troubleshooting):
#   python scripts/download_transcript.py --session N
#   python scripts/prepare_transcript.py --input inbox/transcripts/raw/session-N.txt --session N
#   python scripts/chunk_transcript.py --session N --input inbox/transcripts/prepared/session-N.txt

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
- `/export-kb` - Generate consolidated export files for Claude Project Knowledge, then build and deploy the website

## Architecture

### Directory Structure

- `grimwild-kb/` - Main knowledge base (sessions/, pcs/, npcs/, locations/, items/, factions/, story-arcs/, world/)
- `gm-notes/` - Private GM notes (excluded from player-visible exports)
- `inbox/transcripts/` - Processing pipeline: raw/ → prepared/ → chunks/ (temp) → extracted/ → processed/
- `inbox/notes/` - Planning notes awaiting incorporation
- `config/` - speaker-map.yaml (Discord→character mapping), entity-aliases.yaml (name→filename mapping)
- `exports/` - Generated files for Claude Projects
- `templates/` - Markdown templates for each entity type
- `knowledge/` - Grimwild game system reference material
- `review/` - Conflicts and questions flagged for human review
- `site/` - Quartz static site generator (content/ and public/ are gitignored, built by `/publish-kb`)

### Key Configuration Files

- `config/speaker-map.yaml` - Maps Discord usernames to player/character names, contains transcription corrections
- `config/entity-aliases.yaml` - Maps entity name variants to canonical filenames for wiki-link resolution

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

PCs go in `grimwild-kb/pcs/`, NPCs in `grimwild-kb/npcs/`. Distinguish using `config/speaker-map.yaml` which lists all player characters.

## Workflow Principles

1. **Semi-automated with human review**: Claude proposes changes, user reviews via `git diff` before committing
2. **Context efficiency**: List KB filenames rather than reading all content; read only when needed
3. **Conflict handling**: Flag ambiguous updates in `review/pending-changes.md` for human decision
4. **Private content routing**: GM-only observations go to `gm-notes/`, not `grimwild-kb/`

## Development Reference

Full specifications, templates, and development tasks are documented in `dev/PROJECT.md`.

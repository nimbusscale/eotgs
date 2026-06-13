# Skill: Export Foundry

**Purpose:** Mirror the campaign KB into the `grimwild-kb` Foundry VTT module and
deploy it to the Foundry server, where it appears as a browsable "Campaign KB"
compendium with folders per entity type and show-to-players image pages.

**Output:** Regenerated `compendium/grimwild-kb/` and a deployed module on
`foundry.jjk3.com`.

This is independent of `/export-kb` (the Claude-Project export) and `/publish-kb`
(the Quartz website) — run it whenever the KB content or its illustrations change
and you want the Foundry reference refreshed.

---

## Workflow

### Step 1 — Build the module

```bash
python3 scripts/build_compendium.py
```

Regenerates `compendium/grimwild-kb/src/kb/*.json` (one file per Folder and
JournalEntry) from the KB frontmatter + body, copies referenced hero/gallery
images into `assets/`, and packs the compiled LevelDB into `packs/kb/`.

Review the printed summary: entity counts per folder, page count, images copied,
and **0 missing-image warnings**. The Foundry CLI needs Node 22+ — if packing
fails, run `nvm use 22` first (or `npm install -g @foundryvtt/foundryvtt-cli`).

### Step 2 — Deploy to the Foundry server

```bash
bash scripts/publish_compendium.sh
```

Rebuilds, then `rsync`s `module.json`, `packs/kb`, and `assets/` into
`/home/foundry/foundrydata/Data/modules/grimwild-kb/` on `foundry.jjk3.com`.

### Step 3 — One-time / after-change Foundry steps (manual, GM)

- First time only: in Foundry, **Manage Modules → enable "Echoes of the Godstorm
  — Campaign KB"**.
- After a content change: restart Foundry (or re-open the world) so it re-reads
  the pack, then open the **Campaign KB** compendium.

---

## Notes

- `packs/kb/` and `assets/` are **gitignored** and rebuilt each run; only the
  `src/` JSON and `module.json` are committed.
- Everything is GM-only by default (`ownership.default: 0`). Sharing art is
  per-image via right-click → **Show to Players** on an image page.
- Cross-entry `@UUID` links are derived from deterministic ids, so they survive
  every rebuild. Sub-entity links (e.g. `[[The Chryseum]]`) resolve to their
  parent entry (`Aurelion`), mirroring the website.
- Scope mirrors the site: NPCs, Locations, Factions, Items, World, PCs, Sessions
  (with arc sub-folders). `story-arcs/` and `gm-notes/` are excluded.

# Echoes of the Godstorm

A campaign knowledge base for a tabletop RPG.
It turns Discord voice-channel transcripts into a structured markdown knowledge base optimized for Claude Projects, and publishes a searchable website.

For the full pipeline, architecture, conventions, and slash commands, see [`CLAUDE.md`](CLAUDE.md).
A summary of the current campaign lives in [`exports/campaign-index.md`](exports/campaign-index.md).

## Images and assets

The `images/` directory is **not tracked in git** (it is listed in `.gitignore`).
This is intentional — the generated illustrations are large and would bloat the repo history.

The images are **not lost**: `/export-kb` (via `scripts/publish_site.sh`) mirrors every published image to the production server at `root@foundry.jjk3.com:/var/www/echoes-of-the-godstorm/`, and that server is itself backed up.
So the canonical copy of the images lives on the server, not in the repo.

To regenerate or add an image, use `scripts/generate_image.py` and reference it from `config/image-map.yaml`; the next `/export-kb` copies it into the site build and deploys it.

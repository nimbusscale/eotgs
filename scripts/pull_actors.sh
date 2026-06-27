#!/usr/bin/env bash
# Pull the live Foundry "Echoes of the Godstorm" world's player-character sheets
# to local JSON, then write per-character snapshots into inbox/characters/.
# Usage: bash scripts/pull_actors.sh
#
# This is the remote half of the character sync. It is READ-ONLY against the
# server: rsync copies the world's actors LevelDB pack down, the Foundry CLI
# unpacks it to JSON, and scripts/extract_characters.py renders one snapshot per
# mapped PC. Foundry can stay running — copying the LevelDB files yields a
# consistent enough snapshot between games. Nothing is written back to the server.
#
# Then run /incorporate-characters to fold the snapshots into kb/pcs/ entries
# (reconciling stats/moves into the existing sections; review with git diff).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEPLOY_HOST="root@foundry.jjk3.com"
# The "Echoes of the Godstorm" world (Chasing Adventure on the pbta system).
WORLD="pbta-test"
# v13 world stores each collection as its own LevelDB dir under data/.
REMOTE_ACTORS="/home/foundry/foundrydata/Data/worlds/$WORLD/data/actors/"

# Local scratch (gitignored via the repo's top-level scratch/ rule).
WORK="$REPO_ROOT/scratch/foundry-actors"
LDB_PARENT="$WORK/world-data"   # fvtt unpack wants the *parent* of the pack dir
LDB_DIR="$LDB_PARENT/actors"
JSON_DIR="$WORK/actors-json"

# The Foundry CLI prefers Node 22+; make it available if nvm is installed.
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" && nvm use 22 >/dev/null 2>&1 || true

echo "==> Pulling actors LevelDB from $DEPLOY_HOST ..."
mkdir -p "$LDB_DIR"
rsync -avz "$DEPLOY_HOST:$REMOTE_ACTORS" "$LDB_DIR/"
# The server's copied LOCK file makes classic-level refuse to open the snapshot;
# drop it (we only ever read this local copy).
rm -f "$LDB_DIR/LOCK"

echo ""
echo "==> Unpacking actors to JSON ..."
rm -rf "$JSON_DIR"
mkdir -p "$JSON_DIR"
fvtt package unpack actors --in "$LDB_PARENT" --out "$JSON_DIR"

echo ""
echo "==> Writing character snapshots to inbox/characters/ ..."
python3 "$REPO_ROOT/scripts/extract_characters.py" --input "$JSON_DIR"

echo ""
echo "Next: run /incorporate-characters to fold the snapshots into kb/pcs/ entries."

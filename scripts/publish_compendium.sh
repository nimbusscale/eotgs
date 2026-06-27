#!/usr/bin/env bash
# Regenerate the grimwild-kb Foundry module from the KB and deploy it to the
# Foundry server. Usage: bash scripts/publish_compendium.sh
#
# Enabling the module inside a Foundry *world* is a one-time manual step
# (Manage Modules). After this deploy finishes, re-open the world (or refresh
# the browser) for the GM to see the updated "Campaign KB" compendium.
#
# IMPORTANT: the pack is a LevelDB. LevelDB is NOT safe to swap on disk under a
# live reader — if rsync replaces CURRENT/MANIFEST/*.ldb while Foundry holds the
# pack open, LevelDB runs recovery on the mismatched files, orphans the SSTable
# into a lost/ dir, and the compendium opens EMPTY. So we stop the Foundry
# service before the rsync and start it again after, guaranteeing the DB is
# closed when its files change.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODULE_DIR="$REPO_ROOT/compendium/grimwild-kb"
DEPLOY_HOST="root@foundry.jjk3.com"
FOUNDRY_SERVICE="foundryvtt.service"
# Foundry user-data dir on the server (discovered from Config/options.json).
DATA_MODULES="/home/foundry/foundrydata/Data/modules"
DEST="$DATA_MODULES/grimwild-kb/"

# The Foundry CLI prefers Node 22+; make it available if nvm is installed.
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" && nvm use 22 >/dev/null 2>&1 || true

# Step 1: Rebuild module (regenerates src/kb, copies assets, packs LevelDB).
echo "==> Building grimwild-kb module..."
python3 "$REPO_ROOT/scripts/build_compendium.py"

# Step 2: Stop Foundry so it releases the LevelDB pack before we swap its files.
echo ""
echo "==> Stopping $FOUNDRY_SERVICE (so it releases the LevelDB pack)..."
ssh "$DEPLOY_HOST" "systemctl stop '$FOUNDRY_SERVICE'"

# Always restart Foundry on exit, even if the rsync below fails partway, so we
# never leave the server down.
restart_foundry() {
    echo "==> Starting $FOUNDRY_SERVICE..."
    ssh "$DEPLOY_HOST" "systemctl start '$FOUNDRY_SERVICE'" || true
}
trap restart_foundry EXIT

# Step 3: Deploy. Sync module.json, packs/kb (compiled LevelDB) and assets/.
# src/ is the committed source of truth and node_modules is build-only — neither
# belongs in the deployed module, so both are excluded. We blow away the old
# packs/kb first so no stale LevelDB log/manifest files linger to confuse
# recovery (rsync --delete handles the rest of the tree).
echo ""
echo "==> Deploying to $DEPLOY_HOST:$DEST ..."
ssh "$DEPLOY_HOST" "mkdir -p '$DATA_MODULES/grimwild-kb' && rm -rf '$DATA_MODULES/grimwild-kb/packs/kb'"
rsync -avz --delete \
    --exclude 'src/' \
    --exclude 'node_modules/' \
    "$MODULE_DIR/" "$DEPLOY_HOST:$DEST"

# Step 4: Ensure the Foundry service user can read the module.
ssh "$DEPLOY_HOST" "chown -R foundry:foundry '$DATA_MODULES/grimwild-kb'"

# Step 5: restart_foundry runs here via the EXIT trap.
echo ""
echo "Deployed grimwild-kb. In Foundry: Manage Modules → enable 'Echoes of the"
echo "Godstorm — Campaign KB', then re-open the world (or refresh) and open the"
echo "'Campaign KB' compendium."

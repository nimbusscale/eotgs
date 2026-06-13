#!/usr/bin/env bash
# Regenerate the grimwild-kb Foundry module from the KB and deploy it to the
# Foundry server. Usage: bash scripts/publish_compendium.sh
#
# Enabling the module inside a Foundry *world* is a one-time manual step
# (Manage Modules). After a content change you may need to restart Foundry or
# re-open the world for the GM to see the updated "Campaign KB" compendium.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODULE_DIR="$REPO_ROOT/compendium/grimwild-kb"
DEPLOY_HOST="root@foundry.jjk3.com"
# Foundry user-data dir on the server (discovered from Config/options.json).
DATA_MODULES="/home/foundry/foundrydata/Data/modules"
DEST="$DATA_MODULES/grimwild-kb/"

# The Foundry CLI prefers Node 22+; make it available if nvm is installed.
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" && nvm use 22 >/dev/null 2>&1 || true

# Step 1: Rebuild module (regenerates src/kb, copies assets, packs LevelDB).
echo "==> Building grimwild-kb module..."
python3 "$REPO_ROOT/scripts/build_compendium.py"

# Step 2: Deploy. Sync module.json, packs/kb (compiled LevelDB) and assets/.
# src/ is the committed source of truth and node_modules is build-only — neither
# belongs in the deployed module, so both are excluded.
echo ""
echo "==> Deploying to $DEPLOY_HOST:$DEST ..."
ssh "$DEPLOY_HOST" "mkdir -p '$DATA_MODULES/grimwild-kb'"
rsync -avz --delete \
    --exclude 'src/' \
    --exclude 'node_modules/' \
    "$MODULE_DIR/" "$DEPLOY_HOST:$DEST"

# Step 3: Ensure the Foundry service user can read the module.
ssh "$DEPLOY_HOST" "chown -R foundry:foundry '$DATA_MODULES/grimwild-kb'"

echo ""
echo "Deployed grimwild-kb. In Foundry: Manage Modules → enable 'Echoes of the"
echo "Godstorm — Campaign KB', then open the 'Campaign KB' compendium."

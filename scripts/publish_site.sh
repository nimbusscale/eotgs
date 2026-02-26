#!/usr/bin/env bash
# Build the Grimwild KB as a static site and deploy to production.
# Usage: bash scripts/publish_site.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SITE_DIR="$REPO_ROOT/site"
DEPLOY_HOST="root@foundry.jjk3.com"
DEPLOY_PATH="/var/www/echoes-of-the-godstorm/"
SITE_URL="https://foundry.jjk3.com/echoes-of-the-godstorm/"

# Ensure Node 22 is available
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
nvm use 22 >/dev/null 2>&1

# Step 1: Generate site content (bootstraps Quartz if needed)
echo "==> Generating site content..."
python3 "$REPO_ROOT/scripts/build_site.py"

# Step 2: Build static HTML
echo ""
echo "==> Building static site..."
cd "$SITE_DIR"
npx quartz build

# Step 3: Deploy
echo ""
echo "==> Deploying to $DEPLOY_HOST..."
rsync -avz --delete "$SITE_DIR/public/" "$DEPLOY_HOST:$DEPLOY_PATH"

# Step 4: Verify
echo ""
echo "==> Verifying deployment..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$SITE_URL")
if [ "$HTTP_CODE" = "200" ]; then
    echo "Site is live at $SITE_URL"
else
    echo "WARNING: Site returned HTTP $HTTP_CODE"
    exit 1
fi

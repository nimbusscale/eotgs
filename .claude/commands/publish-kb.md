# Skill: Publish KB

**Purpose:** Build the Grimwild KB as a static website and deploy it to `https://foundry.jjk3.com/echoes-of-the-godstorm/`.

**Output:** Live website at the URL above

---

## Workflow

### Step 1 — Generate site content

Run the build script to copy KB files into the Quartz content directory with injected frontmatter. If `site/` doesn't exist yet, the script will bootstrap Quartz automatically (clone, install deps, apply config). This requires Node 22:

```bash
export NVM_DIR="$HOME/.nvm" && [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" && nvm use 22 && python3 scripts/build_site.py
```

Review the output for any warnings about missing alias targets.

### Step 2 — Build static HTML

Build the Quartz static site:

```bash
cd site && export NVM_DIR="$HOME/.nvm" && [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" && nvm use 22 && npx quartz build
```

Verify the output reports the expected number of files (should be ~55 markdown files → ~210 emitted files).

### Step 3 — Deploy to server

Sync the built files to the production server:

```bash
rsync -avz --delete site/public/ root@foundry.jjk3.com:/var/www/echoes-of-the-godstorm/
```

### Step 4 — Verify deployment

Check that the site is accessible:

```bash
curl -s -o /dev/null -w "%{http_code}" https://foundry.jjk3.com/echoes-of-the-godstorm/
```

Expected: `200`

### Step 5 — Report results

Report to the user:
- URL: `https://foundry.jjk3.com/echoes-of-the-godstorm/`
- Number of pages built
- Any warnings from the build process

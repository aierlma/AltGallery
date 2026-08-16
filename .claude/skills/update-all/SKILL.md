---
name: update-all
description: Regenerate everything in the AltGallery repo — run ./update.sh (regenerate every apps/<AppName>/apps.json from config.toml and merge them into all-apps.json) and ./update_news.sh (re-render every app's images/news.png from its news.toml). Leave the regenerated files uncommitted for the user to review. Use when the user wants to refresh / update / regenerate all app sources and news images.
---

# Update All App Sources & News Images

Refresh every generated artifact in the repo:

1. **Regenerate every app source + merge** — each `apps/<AppName>/apps.json`
   from its `config.toml`, then merged into the repo-root `all-apps.json`:
   ```bash
   ./update.sh
   ```
2. **Re-render every news image** — each `apps/<AppName>/images/news.png`
   from its `news.toml`:
   ```bash
   ./update_news.sh
   ```
   Needs the uv venv set up once (`uv venv && uv pip install -r
   requirements.txt`), plus `rsvg-convert` or macOS Quick Look.

Notes:
- `update.sh` reads the GitHub Releases API; if rate-limited, retry with a
  token, e.g. `GITHUB_TOKEN=$(gh auth token) uvx altgen -c config.toml`.
- Do not auto-commit — leave the changed `apps.json`, `all-apps.json`, and
  `images/news.png` files in the working tree for the user to review and
  commit (AGENTS.md rule: never leave a `config.toml` and its `apps.json`
  out of sync; `all-apps.json` is regenerated whenever any source changes).

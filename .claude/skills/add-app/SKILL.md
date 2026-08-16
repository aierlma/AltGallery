---
name: add-app
description: Add a new app to the AltGallery repo. Creates apps/<AppName>/, writes config.toml and news.toml, downloads icon + screenshots, samples a tint color from the icon, renders images/news.png, generates apps.json with altgen, merges into all-apps.json, and adds the README "Available Apps" entry. Use whenever the user wants to add a new app / a new IPA source to the gallery.
---

# Adding a New App to AltGallery

End-to-end procedure for adding one IPA project to the gallery. Shared
reference details (icon color sampling, news rendering, merge) live in
AGENTS.md — the key gotchas are inlined here, and links point at the full
sections.

## Procedure

1. **Create the folder**
   ```bash
   mkdir -p apps/<AppName>/images
   ```
   Use the project's display name (match the GitHub repo's casing).

2. **Download icon and screenshots**
   Fetch from the project's GitHub repo (e.g. `raw.githubusercontent.com`,
   or the repo's `assets/` folder) into `apps/<AppName>/icon.png` and
   `apps/<AppName>/images/*.png` (~3 portrait shots, e.g. `home.png`,
   `detail.png`, `comment.png`).

3. **Write `config.toml`** modeled on `apps/PiliPlus/config.toml`:
   - `[github]`: `repo = "owner/name"`
   - `[source]`: name, subtitle, description, `website`, and `icon_url`
     pointing at the new app's committed icon
   - `[app]`: name, `bundle_identifier`, `developer_name`, subtitle,
     description, `icon_url`, `screenshots` (the
     `https://raw.githubusercontent.com/bebound/AltGallery/master/apps/<AppName>/images/*.png`
     URLs), `tint_color`, `min_os_version`
   - `[versions]`: matching rules. ⚠️ **`asset_pattern` is a regex, not a
     glob** — to match any ipa use `".*\\.ipa$"`; `"*.ipa"` fails with
     `invalid regex`. Narrow it to a specific filename when each release
     ships exactly one ipa (e.g. `"EhPanda\\.ipa$"`)
   - `[news]`: copy the PiliPlus block, point `image_url` at the new app's
     `images/news.png`
   - `[output]`: `path = "apps.json"`
   - All `raw.githubusercontent.com` URLs use the `bebound/AltGallery`
     repo path.

4. **Sample a tint color** (when the project has no official brand color):
   call the existing sampler in `templates/render_news.py` →
   `extract_icon_color()` instead of re-implementing the sips/BMP pipeline
   (see AGENTS.md → [Icon Color
   Sampling](#icon-color-sampling-macos-sips)):
   ```bash
   PYTHONPATH=templates python3 -c "from render_news import extract_icon_color; from pathlib import Path; print(extract_icon_color(Path('apps/<AppName>/icon.png')))"
   ```
   ⚠️ **Eyeball the result — human confirmation required.** Multi-color or
   pale icons may not have an obvious single brand color.

5. **Write `news.toml`** (`name`, `tagline`, optional `[colors]`), then
   render the shared promo image (AGENTS.md → [Generating News Images]):
   ```bash
   ./.venv/bin/python templates/render_news.py --out apps/<AppName>
   ```
   Renders `apps/<AppName>/images/news.png` (1600x1200, 4:3) into the working
   tree (do not auto-commit). Requires `rsvg-convert` (librsvg) or falls back
   to macOS Quick Look. ⚠️ **Use the venv interpreter** (same as
   `update_news.sh`): bare `python3` has no Pillow, so `render_news.py`
   silently falls back to estimate-based text metrics — the name's vertical
   position and tagline wrapping differ from the measured layout, producing a
   `news.png` that doesn't match what `./update_news.sh` renders.

6. **Generate `apps.json`** — **never hand-edit it**:
   ```bash
   cd apps/<AppName> && uvx altgen -c config.toml
   ```
   ⚠️ **After ANY `config.toml` change, regenerate** — never leave config and
   `apps.json` out of sync. If rate-limited or fetching from a private repo,
   use `GITHUB_TOKEN=$(gh auth token) uvx altgen -c config.toml`.

7. **Merge into `all-apps.json`** — prefer the scripted flow (regenerates
   every source, then merges):
   ```bash
   ./update.sh
   ```
   Or run the merge explicitly with `uvx altgen merge -c assets/merge.toml
   apps/*/apps.json`. Do not auto-commit the updated `all-apps.json` — leave
   it in the working tree for the user to review (AGENTS.md → [Merging into
   all-apps.json]).

8. **Update README** — add the app to **Available Apps**, icon inline before
   the name:
   ```html
   ### <a href="https://github.com/owner/name"><img src="https://raw.githubusercontent.com/bebound/AltGallery/master/apps/<AppName>/icon.png" alt="<AppName> icon" width="24" align="top"> <AppName></a>
   Short one-line description.
   ```
   ⚠️ Use `align="top"` on the icon — `align="center"` renders ~7px low on
   GitHub.

## Checklist
- [ ] `apps/<AppName>/{config.toml, news.toml, icon.png, images/*, apps.json}` all present
- [ ] `apps.json` regenerated after the last config change; never hand-edited
- [ ] `all-apps.json` merged (via `./update.sh`); not auto-committed
- [ ] `images/news.png` rendered; not auto-committed
- [ ] README entry added, icon with `align="top"`

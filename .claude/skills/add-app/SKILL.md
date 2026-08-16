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
   `sips` → BMP → parse with Python `struct` (see AGENTS.md → [Icon Color
   Sampling](#icon-color-sampling-macos-sips) for the exact steps).
   ⚠️ BMP pitfalls: the header `height` may be **negative (top-down)**, and
   `biBitCount` is 24 (BGR) or 32 (BGRA) — read `w * (bpp // 8)` bytes per
   row and treat channels as BGR/A; skip transparent / near-white /
   near-black pixels.
   ⚠️ **Eyeball the result — human confirmation required.** Multi-color or
   pale icons may not have an obvious single brand color.

5. **Write `news.toml`** (`name`, `tagline`, optional `[colors]`), then
   render the shared promo image (AGENTS.md → [Generating News Images]):
   ```bash
   python3 templates/render_news.py --out apps/<AppName>
   ```
   Commits `apps/<AppName>/images/news.png` (1600x1200, 4:3). Requires
   `rsvg-convert` (librsvg) or falls back to macOS Quick Look.

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
   apps/*/apps.json`. Commit the updated `all-apps.json` (AGENTS.md →
   [Merging into all-apps.json]).

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
- [ ] `all-apps.json` merged (via `./update.sh`) and committed
- [ ] `images/news.png` committed
- [ ] README entry added, icon with `align="top"`

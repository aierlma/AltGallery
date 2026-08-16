# AltGallery — Agent Guide

## Project Goal

Generate AltStore sources (`apps.json`) for IPA projects on GitHub, and provide a display page.

- Generator: Python **altgen**, invoked via `uvx altgen`
- Display page: **not implemented yet** (see TODO below)

## Directory Layout

Each IPA gets its own folder, e.g. `PiliPlus/`:

```
<AppName>/
├── config.toml      # altgen configuration file
├── icon.png         # app icon
├── images/          # screenshots + news.png promo image
│   ├── home.png     # screenshots (referenced from [app] screenshots)
│   └── news.png     # generated promo image (referenced from [news] image_url)
└── apps.json        # generated AltStore source, do not hand-edit
```

Each folder's `apps.json` is an independent AltStore source.

## Generating apps.json

Run inside the app's folder:

```bash
cd <AppName>
uvx altgen -c config.toml
```

Note: the config filename is `config.toml` (not config.json).

altgen reads the GitHub Releases API. When rate-limited or accessing private repos, a token is required, with precedence: `--token` flag > `GITHUB_TOKEN` env var > `[github].token` in config.toml.
(Note: the default `GITHUB_TOKEN` in CI only has access to the repo running the workflow; to fetch releases from another repo, use a PAT with public repo read permission.)

## Generating News Images

Each app has a shared `news.png` promo image referenced by all its news entries
via `[news] image_url`. It advertises a generic "NEW UPDATE" (no version
number) — just the app icon, name, and a one-line tagline — so it stays
reusable across releases. Render it from the shared template:

```bash
python3 templates/render_news.py \
  --name <AppName> \
  --tagline "One-line descriptor" \
  --icon icon.png \
  --tint "#app_tint" \
  --tint-alt "#source_tint" \
  --out <AppName>
```

- Output: `<AppName>/images/news.png` (1600x1200, 4:3). The intermediate
  `news.svg` is written inside the app folder (so the icon's relative href
  resolves) and removed afterwards — only the PNG is committed.
- Colors come from `config.toml`: `--tint` = `[app] tint_color`,
  `--tint-alt` = `[source] tint_color`.
- Requires `rsvg-convert` (librsvg) or falls back to macOS Quick Look.
- After rendering, commit `images/news.png`; the URL in `config.toml`
  `[news] image_url` already points at it.

## Existing Apps

- `PiliPlus/` — source repo `bggRGjQaUbCoE/PiliPlus`, `apps.json` generated

## Adding a New App

1. Create the `<AppName>/` folder
2. Write `config.toml` modeled on `PiliPlus/config.toml`:
   - `[github]`: source repo owner/name
   - `[source]`: source-level info (name, icon_url, website, etc.)
   - `[app]`: app info (bundle_identifier, developer_name, icon_url, screenshots, etc.)
   - `[versions]`: version matching rules. ⚠️ `asset_pattern` is a **regex**, not a glob — to match all ipa files use `".*\\.ipa$"`; writing `"*.ipa"` fails with `invalid regex`
   - `[output]`: `path = "apps.json"`
3. Place icons and screenshots (screenshots go in `<AppName>/images/`)
4. Render `images/news.png` (see [Generating News Images](#generating-news-images))
5. Run the generation command above and commit the generated `apps.json`

## Update Flow

Automated via GitHub Actions CI (workflow file not created yet):

- On a schedule or manual trigger, run altgen for each app folder to regenerate `apps.json`
- Commit the changes back to the repo

## TODO

- [ ] Create `.github/workflows/` update CI
- [ ] Display page: render an app list from each folder's `apps.json` (tech stack undecided)

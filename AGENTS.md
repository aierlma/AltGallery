# AltGallery — Agent Guide

## Project Goal

Generate AltStore sources (`apps.json`) for IPA projects on GitHub, and provide a display page.

- Generator: Python **altgen**, invoked via `uvx altgen`
- Display page: **not implemented yet** (see TODO below)

## Reading JSON

Prefer `jq` to read or inspect JSON files (`apps.json`, `all-apps.json`), e.g.
`jq '.apps | length' PiliPlus/apps.json` or `jq '.apps[0]' PiliPlus/apps.json`.
Only read the full file when you actually need the whole content.

## Directory Layout

Each IPA gets its own folder, e.g. `PiliPlus/`:

```
<AppName>/
├── config.toml      # altgen configuration file
├── news.toml        # news image config (name, tagline, optional colors)
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

**Rule: after ANY modification to a `config.toml`, always regenerate the
app's `apps.json` with `uvx altgen -c config.toml` — never leave the two out
of sync, and never hand-edit `apps.json`.**

## Merging into all-apps.json

After all app sources are regenerated, merge them into the repo-root
`all-apps.json` (the "ultimate" AltStore source for the whole project).
The whole flow — regenerate every source, then merge — is scripted in
`./update.sh` (run from anywhere); prefer it over the individual commands.

```bash
uvx altgen merge -c assets/merge.toml <AppName>/apps.json ...
```

Pass **every** `<AppName>/apps.json` in the repo as an input. The merge
config lives in `assets/merge.toml`: merge mode only reads `[source]` (root
metadata: name, icon_url, tint_color) and `[output]` (`path = "../all-apps.json"`,
resolved against the config's directory → repo root).

**Rule: always run `./update.sh` (or the merge) and commit the updated
`all-apps.json` whenever an app's `apps.json` changes (regenerated, new app
added, app removed).**

## Generating News Images

Each app has a shared `news.png` promo image referenced by all its news entries
via `[news] image_url`. It advertises a generic "NEW UPDATE" (no version
number) — just the app icon, name, and a one-line tagline — so it stays
reusable across releases. Render it from the shared template:

```bash
python3 templates/render_news.py --out <AppName>
```

To re-render every app's news image at once (each from its own `news.toml`),
run `./update_news.sh` from anywhere.

- All values come from `<AppName>/news.toml` (`name`, `tagline`, and
  optional `[colors]`); CLI flags (`--name`, `--tagline`, `--tint`,
  `--tint-alt`, `--icon`) override their news.toml counterparts.
- Unset colors are derived into a harmonious scheme:
  - `tint`/`tint_alt` fall back to `[app]`/`[source]` `tint_color`
  - `background` (plus optional `bg_mid`/`bg_dark` stops) defaults to a
    **soft light shade of the app icon's dominant color** — see
    [Icon Color Sampling (macOS sips)](#icon-color-sampling-macos-sips)
    below; falls
    back to a dark tint-derived base when the icon can't be read
  - `text_color` defaults to white, black on light backgrounds (lightness
    > 0.55); `tagline_color` derives from the background hue — both
    adapt to light vs dark backgrounds automatically
  - Pin any of them in `[colors]` to override, e.g. `PiliPlus/news.toml`
    pins the classic dark-blue look.
- Output: `<AppName>/images/news.png` (1600x1200, 4:3). The intermediate
  `news.svg` is written inside the app folder (so the icon's relative href
  resolves) and removed afterwards — only the PNG is committed.
- Requires `rsvg-convert` (librsvg) or falls back to macOS Quick Look.
- After rendering, commit `images/news.png`; the URL in `config.toml`
  `[news] image_url` already points at it.

## Icon Color Sampling (macOS sips)

**sips** is macOS's built-in image tool (always available, no dependencies).
Use it whenever you need to inspect or convert images on this machine —
Python's stdlib cannot decode PNG, so the pattern is: `sips` → BMP → parse
with `struct`.

Useful commands:

```bash
sips -g pixelWidth -g pixelHeight icon.png          # image dimensions
sips -z 64 64 icon.png --out small.png              # resize (w h, preserves aspect)
sips -s format bmp icon.png --out icon.bmp          # convert to BMP for parsing
sips -s format jpeg -s formatOptions 80 in.png --out out.jpg   # format + quality
```

**Sampling a dominant color from an image** (this is how `render_news.py`
derives the light background, and how you should pick a `tint_color` for a
new app's `config.toml`):

1. Downscale to 64×64 and convert to BMP: `sips -s format bmp -z 64 64 icon.png --out /tmp/icon.bmp`
2. Parse with Python `struct` — **BMP pitfalls (all hit before, cost real
   debugging time)**:
   - The BMP header's `height` field may be **negative (top-down)** — read
     the sign at offset 22 and index rows with `y` directly when negative,
     do NOT blindly flip with `h - 1 - y` (a flipped read makes text/badges
     appear at the wrong y and looks like missing elements)
   - Check `biBitCount` at offset 28: sips emits **24bpp (BGR)** or
     **32bpp (BGRA)** — read `w * (bpp // 8)` bytes per row, and pixel
     channels are BGR/A order, not RGB
   - Skip transparent pixels (`alpha < 128` in 32bpp) and near-white /
     near-black (transparency voids, glare, borders)
3. Bucket pixels by color (e.g. `r//16*16`), then score buckets by
   `pixel_count × (saturation − 0.15)`: light-colored designs (e.g.
   Apollo-Reborn's pale icon) must not let their background color win over
   their colorful elements. The top bucket is the "icon color".
4. Use it directly, or derive a harmonious shade: light backgrounds keep the
   hue and push lightness high (`l≈0.88`, `s≤0.35`); dark backgrounds keep
   the hue with low lightness (`l≈0.09`).

For `config.toml` colors: when a new app lacks an official tint, sample its
icon (step 1-3) and use the result as `[app] tint_color` (brand color) —
but eyeball the icon first: a multi-color or pale icon may not have an
obvious single brand color, and the sample needs human confirmation.

## Existing Apps

- `PiliPlus/` — source repo `bggRGjQaUbCoE/PiliPlus`, `apps.json` generated
- `Apollo-Reborn/` — source repo `Apollo-Reborn/Apollo-Reborn` (GLASS variant only, `asset_pattern = "-GLASS\\.ipa$"`), `apps.json` generated
- `Aidoku/` — source repo `Aidoku/Aidoku` (`asset_pattern = "Aidoku\\.ipa$"`), `apps.json` generated

## Adding a New App

1. Create the `<AppName>/` folder
2. Write `config.toml` modeled on `PiliPlus/config.toml`:
   - `[github]`: source repo owner/name
   - `[source]`: source-level info (name, icon_url, website, etc.)
   - `[app]`: app info (bundle_identifier, developer_name, icon_url, screenshots, etc.) — if the project has no official tint_color, sample one from the icon (see [Icon Color Sampling (macOS sips)](#icon-color-sampling-macos-sips))
   - `[versions]`: version matching rules. ⚠️ `asset_pattern` is a **regex**, not a glob — to match all ipa files use `".*\\.ipa$"`; writing `"*.ipa"` fails with `invalid regex`
   - `[output]`: `path = "apps.json"`
3. Place icons and screenshots (screenshots go in `<AppName>/images/`)
4. Write `news.toml` and render `images/news.png` (see [Generating News Images](#generating-news-images))
5. Run the generation command above and commit the generated `apps.json`
6. Re-run the merge (see [Merging into all-apps.json](#merging-into-all-appsjson)) so the new app is included in `all-apps.json`
7. Add the app to the README's **Available Apps** section, with its icon inline before the name (same `raw.githubusercontent.com/bebound/AltGallery/master/<AppName>/icon.png` URL pattern as the existing entries)

## Update Flow

Automated via GitHub Actions CI (workflow file not created yet):

- On a schedule or manual trigger, run `./update.sh` — it regenerates every app source and merges `all-apps.json` (see [Merging into all-apps.json](#merging-into-all-appsjson))
- Commit the changes back to the repo

## TODO

- [ ] Create `.github/workflows/` update CI
- [ ] Display page: render an app list from each folder's `apps.json` (tech stack undecided)

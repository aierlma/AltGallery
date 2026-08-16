<p align="center">
  <img src="https://raw.githubusercontent.com/bebound/AltGallery/master/assets/icon.png" alt="AltGallery" width="120">
</p>

<h1 align="center">AltGallery</h1>

<p align="center">Curated AltStore sources for IPA projects on GitHub. All sources are generated in this repo with <a href="https://github.com/bebound/AltGen">altgen</a>.</p>

<p align="center">
<a href="https://raw.githubusercontent.com/bebound/AltGallery/refs/heads/master/all-apps.json" target="_blank">
<img src="https://raw.githubusercontent.com/bebound/AltGallery/master/assets/add-alt-source.png" alt="Add AltSource" width="200">
</a>
</p>

## Available Sources

### [Aidoku](https://github.com/Aidoku/Aidoku)
A free and open source manga reading application for iOS and iPadOS.

### [Apollo Reborn](https://github.com/Apollo-Reborn/Apollo-Reborn)
A community-maintained iOS tweak that keeps Apollo for Reddit working after its June 2023 shutdown.

### [PiliPlus](https://github.com/bggRGjQaUbCoE/PiliPlus)
A third-party BiliBili client built with Flutter.

## Project Layout

```
AltGallery/
├── assets/               # shared assets: app icon + "Add AltSource" button
│   ├── icon.svg / icon.png
│   └── add-alt-source.svg / add-alt-source.png
├── templates/            # shared news-image template + renderer
│   ├── news_update.template.svg
│   └── render_news.py
├── <AppName>/            # one folder per app
│   ├── config.toml       # altgen configuration
│   ├── news.toml         # news image config (name, tagline, optional colors)
│   ├── icon.png          # resource files live here
│   ├── images/           # screenshots + news.png promo image
│   └── apps.json         # generated AltStore source
└── ...
```

## Generating News Images

The same `news.png` is referenced by all news entries via `[news] image_url`,
so it advertises a generic "NEW UPDATE" (no version number) — just the app
icon, name, and a one-line tagline. The 4:3 image (1600x1200) is deliberately
minimal so it stays readable on a landscape phone and two or more fit on one
screen. Reuse the template for a new app:

```bash
python3 templates/render_news.py --out <AppName>
```

All values come from `<AppName>/news.toml` — `name`, `tagline`, and optional
colors under `[colors]` (`tint`, `tint_alt`, `background`, `bg_mid`,
`bg_dark`, `text_color`, `tagline_color`). Colors left unset are derived into
a harmonious scheme: tint colors from `config.toml`, and the background
defaults to a soft light shade of the app icon's dominant color. CLI flags
(`--name`, `--tagline`, `--tint`, ...) override news.toml. Output is
`<AppName>/images/news.png` — the intermediate `news.svg` is created inside
the app folder and removed afterwards, not committed. Requires `rsvg-convert`
(librsvg) or falls back to macOS Quick Look.

## Regenerating a Source

```bash
cd <AppName>
uvx altgen -c config.toml
```

Sources are updated automatically via GitHub Actions (workflow pending).

## Roadmap

- [ ] CI workflow to regenerate `apps.json` on a schedule
- [ ] Display page listing all available apps

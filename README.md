# AltGallery

Curated AltStore sources for IPA projects on GitHub. Some sources are generated in this repo with [altgen](https://github.com/bebound/AltGen). Other sources are maintained by their own projects and linked here for convenience.

## Available Sources

### [Aidoku](https://github.com/Aidoku/Aidoku)
A free and open source manga reading application for iOS and iPadOS.

<a href="https://raw.githubusercontent.com/Aidoku/Aidoku/altstore/apps.json" target="_blank">
<img src="https://github.com/CelloSerenity/altdirect/blob/main/assets/png/AltSource_Blue.png?raw=true" alt="Add AltSource" width="200">
</a>

### [Apollo Reborn](https://github.com/Apollo-Reborn/Apollo-Reborn)
A community-maintained iOS tweak that keeps Apollo for Reddit working after its June 2023 shutdown.

<a href="https://raw.githubusercontent.com/Apollo-Reborn/Apollo-Reborn/refs/heads/main/apps_glass.json" target="_blank">
<img src="https://github.com/CelloSerenity/altdirect/blob/main/assets/png/AltSource_Blue.png?raw=true" alt="Add AltSource" width="200">
</a>

### [PiliPlus](https://github.com/bggRGjQaUbCoE/PiliPlus)
A third-party BiliBili client built with Flutter.

<a href="https://altdirect.app/?url=https://raw.githubusercontent.com/bebound/AltGallery/refs/heads/master/PiliPlus/apps.json" target="_blank">
<img src="https://github.com/CelloSerenity/altdirect/blob/main/assets/png/AltSource_Blue.png?raw=true" alt="Add AltSource" width="200">
</a>

## Project Layout

```
AltGallery/
├── templates/            # shared news-image template + renderer
│   ├── news_update.template.svg
│   └── render_news.py
├── <AppName>/            # one folder per app
│   ├── config.toml       # altgen configuration
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
python3 templates/render_news.py \
  --name <AppName> \
  --tagline "One-line descriptor" \
  --icon icon.png \
  --tint "#app_tint" \
  --tint-alt "#source_tint" \
  --out <AppName>
```

Output is `<AppName>/images/news.png` — the intermediate `news.svg` is created
inside the app folder and removed afterwards, not committed. Colors should
come from `config.toml` (`[app] tint_color` / `[source] tint_color`).
Requires `rsvg-convert` (librsvg) or falls back to macOS Quick Look.

## Regenerating a Source

```bash
cd <AppName>
uvx altgen -c config.toml
```

Sources are updated automatically via GitHub Actions (workflow pending).

## Roadmap

- [ ] CI workflow to regenerate `apps.json` on a schedule
- [ ] Display page listing all available apps

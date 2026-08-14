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
├── <AppName>/            # one folder per app
│   ├── config.toml       # altgen configuration
│   ├── icon.png          # resource files live here
│   ├── screenshots/
│   └── apps.json         # generated AltStore source
└── ...
```

## Regenerating a Source

```bash
cd <AppName>
uvx altgen -c config.toml
```

Sources are updated automatically via GitHub Actions (workflow pending).

## Roadmap

- [ ] CI workflow to regenerate `apps.json` on a schedule
- [ ] Display page listing all available apps

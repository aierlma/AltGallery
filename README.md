# AltGallery

Curated AltStore sources for IPA projects on GitHub. Some sources are generated in this repo with [altgen](https://github.com/bebound/AltGen) — each app keeps its own folder with a config and its resource files, and the generated `apps.json` is an independent AltStore source ready to be sideloaded. Other sources are maintained by their own projects and linked here for convenience.

## Available Sources

### PiliPlus

Unofficial AltStore source for [PiliPlus](https://github.com/bggRGjQaUbCoE/PiliPlus), a third-party BiliBili client built with Flutter.

<a href="https://altdirect.app/?url=https://raw.githubusercontent.com/bebound/AltGallery/refs/heads/master/PiliPlus/apps.json" target="_blank">
<img src="https://github.com/CelloSerenity/altdirect/blob/main/assets/png/AltSource_Blue.png?raw=true" alt="Add AltSource" width="200">
</a>

## Project Layout

```
AltGallery/
├── README.md
├── agent.md              # dev/agent guide
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

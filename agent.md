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
├── resource files (icons, screenshots, etc.)
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
3. Place icons, screenshots, and other resource files
4. Run the generation command above and commit the generated `apps.json`

## Update Flow

Automated via GitHub Actions CI (workflow file not created yet):

- On a schedule or manual trigger, run altgen for each app folder to regenerate `apps.json`
- Commit the changes back to the repo

## TODO

- [ ] Create `.github/workflows/` update CI
- [ ] Display page: render an app list from each folder's `apps.json` (tech stack undecided)

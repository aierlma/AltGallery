<p align="center">
  <img src="https://raw.githubusercontent.com/bebound/AltGallery/master/assets/icon.png" alt="AltGallery" width="120">
</p>

<h1 align="center">AltGallery</h1>

<p>Curated AltStore sources for IPA projects on GitHub. All sources are generated in this repo with <a href="https://github.com/bebound/AltGen">AltGen</a>. It can be used with <a href="https://github.com/altstoreio/Altstore">AltStore</a>, <a href="https://github.com/SideStore/SideStore">SideStore</a>, <a href="https://github.com/LiveContainer/LiveContainer">LiveContainer</a>, <a href="https://github.com/claration/Feather">Feather</a> or other compatible apps.</p>

<p align="center">
<a href="https://altdirect.app/?url=https://raw.githubusercontent.com/bebound/AltGallery/refs/heads/master/all-apps.json" target="_blank">
<img src="https://raw.githubusercontent.com/bebound/AltGallery/master/assets/add-alt-source.png" alt="Add AltSource" width="200">
</a>
</p>

## Available Apps

### <a href="https://github.com/Aidoku/Aidoku"><img src="https://raw.githubusercontent.com/bebound/AltGallery/master/apps/Aidoku/icon.png" alt="Aidoku icon" width="24" align="top"> Aidoku</a>
A free and open source manga reading application for iOS and iPadOS.

### <a href="https://github.com/Apollo-Reborn/Apollo-Reborn"><img src="https://raw.githubusercontent.com/bebound/AltGallery/master/apps/Apollo-Reborn/icon.png" alt="Apollo Reborn icon" width="24" align="top"> Apollo Reborn</a>
A community-maintained iOS tweak that keeps Apollo for Reddit working after its June 2023 shutdown.

### <a href="https://github.com/OatmealDome/dolphin-ios"><img src="https://raw.githubusercontent.com/bebound/AltGallery/master/apps/DolphiniOS/icon.png" alt="DolphiniOS icon" width="24" align="top"> DolphiniOS</a>
Dolphin for iOS, reborn — a GameCube and Wii emulator for iPhone and iPad.

### <a href="https://github.com/EhPanda-Team/EhPanda"><img src="https://raw.githubusercontent.com/bebound/AltGallery/master/apps/EhPanda/icon.png" alt="EhPanda icon" width="24" align="top"> EhPanda</a>
An unofficial E-Hentai App for iOS built with SwiftUI & TCA.

### <a href="https://github.com/XITRIX/iTorrent"><img src="https://raw.githubusercontent.com/bebound/AltGallery/master/apps/iTorrent/icon.png" alt="iTorrent icon" width="24" align="top"> iTorrent</a>
Torrent client for iOS.

### <a href="https://github.com/Predidit/Kazumi"><img src="https://raw.githubusercontent.com/bebound/AltGallery/master/apps/Kazumi/icon.png" alt="Kazumi icon" width="24" align="top"> Kazumi</a>
基于自定义规则的番剧采集APP，支持流媒体在线观看、弹幕与实时超分辨率。

### <a href="https://github.com/kodjodevf/mangayomi"><img src="https://raw.githubusercontent.com/bebound/AltGallery/master/apps/Mangayomi/icon.png" alt="Mangayomi icon" width="24" align="top"> Mangayomi</a>
Read manga, novels, and watch anime.

### <a href="https://github.com/bggRGjQaUbCoE/PiliPlus"><img src="https://raw.githubusercontent.com/bebound/AltGallery/master/apps/PiliPlus/icon.png" alt="PiliPlus icon" width="24" align="top"> PiliPlus</a>
使用Flutter开发的BiliBili第三方客户端。

### <a href="https://github.com/infinityf4p/TiebaPure-iOS"><img src="https://raw.githubusercontent.com/bebound/AltGallery/master/apps/TiebaPure/icon.png" alt="TiebaPure icon" width="24" align="top"> TiebaPure</a>
原生 SwiftUI 构建的非官方贴吧 iOS 客户端，支持浏览、搜索、收藏、媒体查看与本地阅读记录。

### <a href="https://github.com/utmapp/UTM"><img src="https://raw.githubusercontent.com/bebound/AltGallery/master/apps/UTM/icon.png" alt="UTM icon" width="24" align="top"> UTM</a>
A full featured virtual machine host for iOS — run Windows, Android, and more on your iPhone and iPad.

## Project Layout

```
AltGallery/
├── assets/               # shared assets: app icon + "Add AltSource" button
│   ├── icon.svg / icon.png
│   └── add-alt-source.svg / add-alt-source.png
├── templates/            # shared news-image template + renderer
│   ├── news_update.template.svg
│   └── render_news.py
├── apps/                 # one folder per app
│   └── <AppName>/
│       ├── config.toml   # altgen configuration
│       ├── news.toml     # news image config (name, tagline, optional colors)
│       ├── icon.png      # resource files live here
│       ├── images/       # screenshots + news.png promo image
│       └── apps.json     # generated AltStore source
└── ...
```

## Updating Apps and News Images

Run both scripts from the repo root:

```bash
./update.sh       # regenerate every app's apps.json from config.toml and merge into all-apps.json
./update_news.sh  # re-render every app's images/news.png from its news.toml
```

Both scripts can be run from anywhere — paths resolve against the repo
directory. Regenerated files are left uncommitted for you to review.

`update.sh` runs `uvx altgen -c config.toml` in every `apps/<AppName>/` that has
a `config.toml`, then merges the resulting sources into the repo-root
`all-apps.json` via `uvx altgen merge -c assets/merge.toml`.

`update_news.sh` renders each app's `images/news.png` from its `news.toml` using
`templates/render_news.py`. It needs the Python venv (set up once):

```bash
uv venv && uv pip install -r requirements.txt
```

It also requires `rsvg-convert` (librsvg) or falls back to macOS Quick Look.

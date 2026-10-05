# PiliPlus BTR

这是 [nishuodedui1145-del/PiliPlus](https://github.com/nishuodedui1145-del/PiliPlus) 的个人衍生版条目，与 Gallery 现有的官方 PiliPlus 独立。BTR 通过本地 HTTP 代理、多 Range 并发和 CDN 选择/竞速改善海外点播体验，提供设置、快设与日志；总开关默认关闭，需在音视频设置中开启。

## 版本与验证

本源只接收 `PiliPlus-BTR-ios-<version>-btr.<revision>-unsigned.ipa` 正式附件，排除 APK、draft、预发布以及单独的 iOS 14 包。当前保留最新一版；新闻标题保留完整 BTR tag，安装版本字段取自实际 IPA。

2026-10-05 下载并仅解析 [v2.1.4-btr.15 正式附件](https://github.com/nishuodedui1145-del/PiliPlus/releases/tag/v2.1.4-btr.15) 得到：

| 字段 | 正式 IPA 的值 |
|---|---|
| Bundle identifier | `com.example.piliplus.btr` |
| CFBundleShortVersionString | `2.1.4` |
| CFBundleVersion | `5418` |
| MinimumOSVersion | `15.0` |
| 大小 | 24,352,309 bytes |
| SHA-256 | `015f6ef4e60150dd4c49145efd12b0349b94857c75aa8b7fa9e450dc560701b8` |

`com.example.piliplus.btr` 是正式包实际使用的标识符，尽管名称看似占位符。构建号不能由 `btr.15` 推导，也不能使用另一份 CI 构建的编号。

`generate.py` 使用 AltGen 筛选 GitHub Releases，然后下载选中的 IPA，核对大小、发布记录提供的 SHA-256 和 bundle ID，读取主应用 plist 中的版本、构建号和最低系统要求。仅在全部验证成功后原子替换 `apps.json`，临时下载随后清理；不会执行 IPA。新附件命名改变、下载失败或 bundle ID 改变时，本条目报错并保留上一份源，`update.sh` 继续生成其他应用与合并。

本次 1024×1024 图标和三张截图来自该 fork 的 iOS artwork 与 `assets/screenshots/`。截图展示与官方共享的 PiliPlus 界面，不代表 BTR 设置页。

## 更新与上游同步

合并到 `aierlma/AltGallery` 的 `master` 后，现有生成工作流在 master push、每 6 小时的计划任务或手动触发时刷新本源。订阅用户自己的 [AltGallery 合集](https://raw.githubusercontent.com/aierlma/AltGallery/refs/heads/master/all-apps.json) 才能获得这个额外条目；合并前不会上线。生成的 `apps.json` 和 `all-apps.json` 由 CI 提交，贡献者不提交它们。

该 fork 的[正式版更新接口](https://github.com/nishuodedui1145-del/PiliPlus/blob/v2.1.4-btr.15/lib/http/api.dart#L411-L413)和[当前下载回退地址](https://github.com/nishuodedui1145-del/PiliPlus/blob/3988e6d081a26120ca79f1e654fe1a3422b7282f/lib/utils/update.dart#L146)仍指向官方 PiliPlus。若要保留 BTR，请通过本 Gallery 条目更新；应用内的官方更新提示不代表 BTR 已发布新版。

跟踪 fork 的发布不会同步它的源码。2026-10-05 的[上游比较](https://github.com/bggRGjQaUbCoE/PiliPlus/compare/main...nishuodedui1145-del:btr)显示 BTR 分支领先 27 个、落后 61 个提交；是否合并官方改动和重新发布由该 fork 的维护者决定。若需要自己维护源码，应另建用户自己的 PiliPlus fork，以官方 `main` 为 upstream，保留 BTR 分支，定期合并、解决冲突、测试并构建发布。这需要单独的维护范围与构建资源，本次未创建源码 fork 或修改其更新接口。

AltGallery 本身仍可合并 `bebound/AltGallery` 的 upstream 更新，同时保留独立的 `apps/PiliPlus-BTR/`。本次只扩展生成入口，并将个人合集入口、合集元数据与新增素材地址指向 `aierlma/AltGallery`，没有批量改写现有应用；将来同步时检查 `update.sh` 的自定义入口以及这几处个人链接即可。本次未启用额外自动合并任务。

## 本地验证

```sh
./update.sh PiliPlus-BTR
uv venv
uv pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
```

`uv run --no-project --script apps/PiliPlus-BTR/generate.py` 也可独立生成该条目。直接调用 `uvx altgen -c config.toml` 不会解析 IPA 元数据，请使用上述入口。

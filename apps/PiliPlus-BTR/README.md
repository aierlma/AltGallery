# PiliPlus BTR

这是 [aierlma/PiliPlus](https://github.com/aierlma/PiliPlus) 的个人维护版条目，保留 [nishuodedui1145-del/PiliPlus](https://github.com/nishuodedui1145-del/PiliPlus) 的 BTR 改动，与 Gallery 现有的官方 PiliPlus 独立。BTR 通过本地 HTTP 代理、多 Range 并发和 CDN 选择/竞速改善海外点播体验，提供设置、快设与日志；总开关默认关闭，需在音视频设置中开启。

## 版本与验证

本源只接收 `PiliPlus-BTR-ios-<version>-btr.<revision>-unsigned.ipa` 正式附件，排除 APK、draft、预发布以及单独的 iOS 14 包。当前保留最新一版；新闻标题保留完整 BTR tag，安装版本字段取自实际 IPA。

2026-10-05 下载并仅解析自己 fork 的 [v2.1.6-btr.5485-b3109a6274f1 正式附件](https://github.com/aierlma/PiliPlus/releases/tag/v2.1.6-btr.5485-b3109a6274f1) 得到：

| 字段 | 正式 IPA 的值 |
|---|---|
| Bundle identifier | `com.example.piliplus.btr` |
| CFBundleShortVersionString | `2.1.6` |
| CFBundleVersion | `5485` |
| MinimumOSVersion | `15.0` |
| 大小 | 24,443,690 bytes |
| SHA-256 | `0185683b2bf209a4ff0f9965ef65176d76589b472c0abbb06971290e318d28de` |

`com.example.piliplus.btr` 是正式包实际使用的标识符，尽管名称看似占位符。构建号始终从实际包读取，不能使用另一份 CI 构建的编号。原 fork 的 btr.15 基线也已解析验证，为 2.1.4 / 5418 / iOS 15.0。

`generate.py` 使用 AltGen 筛选 GitHub Releases，然后下载选中的 IPA，核对大小、发布记录提供的 SHA-256 和 bundle ID，读取主应用 plist 中的版本、构建号和最低系统要求。仅在全部验证成功后原子替换 `apps.json`，临时下载随后清理；不会执行 IPA。新附件命名改变、下载失败或 bundle ID 改变时，本条目报错并保留上一份源，`update.sh` 继续生成其他应用与合并。

[首个 GitHub 构建与发布](https://github.com/aierlma/PiliPlus/actions/runs/37331343799)通过 45 项 BTR 测试和 8 项维护流程测试；静态分析无错误或警告，37 条继承的提示级 lint 保留输出，不阻断发布。另一次[无更新检查](https://github.com/aierlma/PiliPlus/actions/runs/37347929498)确认跳过构建与发布。

本次 1024×1024 图标和三张截图来自该 fork 的 iOS artwork 与 `assets/screenshots/`。截图展示与官方共享的 PiliPlus 界面，不代表 BTR 设置页。

## 更新与上游同步

合并到 `aierlma/AltGallery` 的 `master` 后，现有生成工作流在 master push、每 6 小时的计划任务或手动触发时刷新本源。订阅用户自己的 [AltGallery 合集](https://raw.githubusercontent.com/aierlma/AltGallery/refs/heads/master/all-apps.json) 才能获得这个额外条目；合并前不会上线。生成的 `apps.json` 和 `all-apps.json` 由 CI 提交，贡献者不提交它们。

源码维护与构建由 [aierlma/PiliPlus 的 GitHub Actions](https://github.com/aierlma/PiliPlus/actions/workflows/btr-maintain.yml) 执行，每天检查官方 main 一次。只有 BTR 接线验证、测试、静态分析、iOS 构建和 IPA 元数据验证全部通过，才快进个人 BTR 分支并发布正式 IPA；发生冲突或验证失败则保留上一正式版本，记录失败 issue，相同输入不会每天重复构建。具体门槛、停止及恢复操作见[个人 fork 说明](https://github.com/aierlma/PiliPlus#同步与发布)。

自己的应用内更新 API、源码链接和下载回退地址均指向 `aierlma/PiliPlus`。它保留原 BTR 的独立 bundle ID，避免切回官方包。GitHub 中的源码合并、测试与构建不等同于真机播放验收；不调用 Codex 的定时会话或本地常驻任务。

AltGallery 通过已有每 6 小时的生成工作流获取个人 fork 最新的正式 IPA，不需要跨仓库访问令牌。这里跟踪的是实际构建结果；不能从官方已有提交推断一个尚未构建通过的个人 IPA 已经发布。

AltGallery 本身仍可合并 `bebound/AltGallery` 的 upstream 更新，同时保留独立的 `apps/PiliPlus-BTR/`。本次只扩展生成入口，并将个人合集入口、合集元数据与新增素材地址指向 `aierlma/AltGallery`，没有批量改写现有应用；将来同步时检查 `update.sh` 的自定义入口以及这几处个人链接即可。本次未启用额外自动合并任务。

## 本地验证

```sh
./update.sh PiliPlus-BTR
uv venv
uv pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
```

`uv run --no-project --script apps/PiliPlus-BTR/generate.py` 也可独立生成该条目。直接调用 `uvx altgen -c config.toml` 不会解析 IPA 元数据，请使用上述入口。

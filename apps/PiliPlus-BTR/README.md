# PiliPlus BTR

这是 [aierlma/PiliPlus](https://github.com/aierlma/PiliPlus) 的个人维护版条目，保留 [nishuodedui1145-del/PiliPlus](https://github.com/nishuodedui1145-del/PiliPlus) 的 BTR 改动，与 Gallery 现有的官方 PiliPlus 独立。BTR 通过本地 HTTP 代理、多 Range 并发和 CDN 选择/竞速改善海外点播体验，提供设置、快设与日志；总开关默认关闭，需在音视频设置中开启。

## 版本与验证

本源只接收 `PiliPlus-BTR-ios-<version>-btr.<revision>-unsigned.ipa` 正式附件，排除 APK、draft、预发布以及单独的 iOS 14 包。当前保留最新一版；新闻标题保留完整 BTR tag，安装版本字段取自实际 IPA。

2026-10-05 下载并仅解析自己 fork 的 [v2.1.6-btr.5488-aa2e954d1547 正式附件](https://github.com/aierlma/PiliPlus/releases/tag/v2.1.6-btr.5488-aa2e954d1547) 得到：

| 字段 | 正式 IPA 的值 |
|---|---|
| Bundle identifier | `com.example.piliplus.btr` |
| CFBundleShortVersionString | `2.1.6` |
| CFBundleVersion | `5488` |
| MinimumOSVersion | `15.0` |
| 大小 | 24,443,570 bytes |
| SHA-256 | `75e9e2f0362768b9e2a51838e590f1bdcdb4112cd5360ff87cacc3ae85998faa` |

`com.example.piliplus.btr` 是正式包实际使用的标识符，尽管名称看似占位符。构建号始终从实际包读取，不能使用另一份 CI 构建的编号。原 fork 的 btr.15 基线也已解析验证，为 2.1.4 / 5418 / iOS 15.0。

`generate.py` 使用 AltGen 筛选 GitHub Releases，然后下载选中的 IPA，核对大小、发布记录提供的 SHA-256 和 bundle ID，读取主应用 plist 中的版本、构建号和最低系统要求。仅在全部验证成功后原子替换 `apps.json`，临时下载随后清理；不会执行 IPA。新附件命名改变、下载失败或 bundle ID 改变时，本条目报错并保留上一份源，`update.sh` 继续生成其他应用与合并。

[首个 GitHub 构建与发布](https://github.com/aierlma/PiliPlus/actions/runs/37331343799)通过 45 项 BTR 测试和 8 项维护流程测试；静态分析无错误或警告，37 条继承的提示级 lint 保留输出，不阻断发布。另一次[无更新检查](https://github.com/aierlma/PiliPlus/actions/runs/37347929498)确认跳过构建与发布。

[双上游 GitHub 构建](https://github.com/aierlma/PiliPlus/actions/runs/37354822916)通过 15 项维护测试、45 项 BTR 测试和 iOS 构建。构建清单记录个人、PiliPlus 官方和 BTR 作者三个 SHA；[三者均无变化的检查](https://github.com/aierlma/PiliPlus/actions/runs/37356373282)确认跳过重复构建。

本次 1024×1024 图标和三张截图来自该 fork 的 iOS artwork 与 `assets/screenshots/`。截图展示与官方共享的 PiliPlus 界面，不代表 BTR 设置页。

## 更新与上游同步

该条目已合并到 `aierlma/AltGallery` 的 `master`。现有生成工作流在 master push、每 6 小时的计划任务或手动触发时刷新本源。可以订阅 [AltGallery 合集](https://raw.githubusercontent.com/aierlma/AltGallery/refs/heads/master/all-apps.json)，也可以在 SideStore 单独添加 [PiliPlus BTR 源](https://raw.githubusercontent.com/aierlma/AltGallery/refs/heads/master/apps/PiliPlus-BTR/apps.json)。生成的 `apps.json` 和 `all-apps.json` 由 CI 提交，贡献者不提交它们。

从 [个人 fork 的版本修复](https://github.com/aierlma/PiliPlus/pull/6) 起，正式 iOS 包使用 `官方主版本.官方次版本.个人构建号` 作为短版本号，例如基于官方 `2.1.6` 的 build 5502 在 SideStore 显示为 `2.1.5502`。官方原版本仍保存在应用内、IPA 的 `PiliPlusUpstreamVersion`、构建清单的 `upstream_version` 和 Release 说明中；Tag/附件名继续包含官方版本与构建号。本源的 `version` 和 `buildVersion` 均读取实际 IPA，不能只把订阅版本写高。发布前要求新短版本和构建号都高于上一正式版，拒绝重复或倒退；纯维护改动仍不发布新包。

在 SideStore 从上述源安装或关联 PiliPlus BTR，然后在 My Apps 下拉刷新源；有新正式包时点 **Update**，SideStore 会从源下载、签名并覆盖安装，无需手动下载 IPA。**Refresh** 只续签。已安装包与源未关联时，请从源中的 PiliPlus BTR 条目安装/关联，保留同一个 bundle ID。通知横幅还需启用 SideStore 通知权限及系统允许的后台检查。更新先等待个人 fork 的 GitHub 合并、测试和发布，再等待本源每 6 小时的生成；没有新包或包验证失败时保留上一正式版。

源码维护与构建由 [aierlma/PiliPlus 的 GitHub Actions](https://github.com/aierlma/PiliPlus/actions/workflows/btr-maintain.yml) 执行，每天分别检查 BTR 作者 `nishuodedui1145-del/PiliPlus/btr` 和 PiliPlus 官方 `bggRGjQaUbCoE/PiliPlus/main`。任一来源有新提交都独立触发合并、测试与构建，不需要等待 BTR 作者先跟上新版官方；之后合入 BTR 新提交时也不会直接覆盖回作者所用的旧官方代码。只有 BTR 接线验证、测试、静态分析、iOS 构建和 IPA 元数据验证全部通过，才快进个人 BTR 分支并发布正式 IPA；发生冲突或验证失败则保留上一正式版本，记录失败 issue，相同的个人、官方和 BTR 三个 SHA 输入不会每天重复构建。具体门槛、停止及恢复操作见[个人 fork 说明](https://github.com/aierlma/PiliPlus#同步与发布)。

自己的应用内更新 API、源码链接和下载回退地址均指向 `aierlma/PiliPlus`。它保留原 BTR 的独立 bundle ID，避免切回官方包。任一来源产生源码冲突时，整个候选回滚并记录 issue，待维护者处理；未启用 LLM 自动修复。GitHub 中的源码合并、测试与构建不等同于真机播放验收；不调用 Codex 的定时会话或本地常驻任务。

AltGallery 通过已有每 6 小时的生成工作流获取个人 fork 最新的正式 IPA，不需要跨仓库访问令牌。这里跟踪的是实际构建结果；不能从官方已有提交推断一个尚未构建通过的个人 IPA 已经发布。

另有 `Sync watched release sources` 每小时第 23 分钟检查一次正式发布的 `build-info.json`，比较其中的实际 IPA 版本、构建号、大小、最低系统要求与下载链接是否已经进入独立源和合集。两者一致时不下载 IPA、不重生成；不一致时只调用现有 BTR 生成器，再合并全部已有条目。生成器仍下载并解析实际 IPA；发布记录不能代替包验证。全量和定向任务共享写入并发组，开始执行时读取当前 master，更新后的两个源在同一个提交里发布。全量任务也检查 BTR 是否真正收录，避免生成成功但仍悄悄落后。

该机制由 `assets/source-watch.toml` 声明需要跟踪的应用，可复用于提供相同实际 IPA 元数据约定的项目。只使用 AltGallery 自己的 GitHub 内置令牌，不新增跨仓库令牌。GitHub 的计划任务仍可能延迟或被丢弃，因此不承诺实时推送；应用内会等订阅源收录后才提示可更新。用户刷新现有源后从 My Apps 更新即可，订阅 URL 与应用标识保持原值。

源版本只允许向前：旧 API 响应不能覆盖已经生成的较新版本，同一版本与构建号不能换成另一个 IPA 链接。全量生成快结束时又有新正式包发布，也会补一次定向检查；无法收敛时工作流明确失败并保留可用源。

AltGallery 源码仓库的上游是 `bebound/AltGallery`，其源码更新目前需要单独维护。本次双上游自动合并作用于个人 PiliPlus 源码；AltGallery 继续自动生成应用订阅，保留官方 PiliPlus 和其他应用。

## 本地验证

```sh
./update.sh PiliPlus-BTR
uv venv
uv pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
```

`uv run --no-project --script apps/PiliPlus-BTR/generate.py` 也可独立生成该条目。直接调用 `uvx altgen -c config.toml` 不会解析 IPA 元数据，请使用上述入口。

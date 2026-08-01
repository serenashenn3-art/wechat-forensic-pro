# Release v2.0.8 — README 头部重做 + 报告样例 + AGENTS 摘要

> **累积变更**: 本次 release 同时回填 **v2.0.6** 和 **v2.0.7** 的变更说明
> (那两个版本的代码已 push 但当时未发 GitHub Release,详见文末"累积变更")

## 一句话总结

把 README 从"长但难找到入口"变成"2 屏内进入 Quick Start",
把 AGENTS.md 从"AI 才知道的硬约束"变成"60 秒可审计的人类摘要",
并附一份完整的脱敏报告样例,让客户 / 法官 / 评审能直观看到输出长什么样。

## 改进 (4 大类)

### 1. README 双语头部重做
- ✅ **Quick Start 上提到第 2 屏** — 3 步搞定,新人立刻能跑
- ✅ **法律声明改为 `<details>` 折叠** — 默认只占一行,需要时再展开
- ✅ **顶部新增 📑 目录 (TOC)** — 11 个章节一键跳转
- ✅ **新增 🛡 AGENTS.md 核心约束 (摘要)** — 200+ 行的 `AGENTS.md` 浓缩成 4 条硬性禁止 + 5 类合法场景 + 6 类反 prompt-injection 模式,合规/法务无需打开 `AGENTS.md` 即可审阅
- ✅ **新增 Tests 62 passed 徽章**

### 2. `examples/sample-report/` — 全新脱敏报告样例目录
- `README.md` — 阅读指引
- `_forensic_report.json` — 机器可读完整 schema (v2.0.8)
- `_forensic_report.txt` — 排版后人类可读文本
- `_signature.json` — HMAC 签名 + 密钥指纹
- `_forensic_manifest.json` — 每文件 SHA-256 清单
- `operations_summary.md` — 操作时间线
- `chat_excerpt_redacted.txt` — 脱敏聊天摘录

**所有标识符、哈希值、聊天内容**都是合成的 mock,**不来自任何真实案件**。

### 3. `scripts/sync_agent_compat.sh` (v2.0.7 同步)
- 防 AGENTS.md 改动后 6 个 mirror 漂移
- `--check` 模式: CI 检测到漂移即 fail PR

### 4. 回填 v2.0.6 + v2.0.7 发布说明
之前两个版本未发 GitHub Release(代码已 push 但 release 页面停留在 v2.0.5),
本次在 v2.0.8 的 release notes 里统一说明累积变更。

## 文件变更

| 类型 | 路径 |
|---|---|
| 修改 | `README.md` (头部 + AGENTS 摘要 + 样例引用) |
| 修改 | `README.zh-CN.md` (同上) |
| **新增** | `examples/sample-report/` (7 个文件) |
| 修改 | `examples/README.md` (新增"报告样例"小节) |
| 修改 | `pyproject.toml` / `wechat_forensic/__init__.py` / `tests/test_cli.py` (2.0.7 → 2.0.8) |
| 修改 | `CHANGELOG.md` (追加 v2.0.8 条目) |
| 修改 | `AGENTS.md` (6 个 mirror 通过 `scripts/sync_agent_compat.sh` 同步) |

## 验证

- ✅ 62/62 pytest 通过
- ✅ `python -m wechat_forensic.cli --version` → `wechat-forensic 2.0.8`
- ✅ 6 个 agent mirror SHA-256 完全一致
- ✅ `bash scripts/sync_agent_compat.sh --check` → 全 OK
- ✅ 样例 JSON 通过 `json.loads()` 解析,11 个 top-level fields
- ✅ Commit `e389de3` 已 push 到 `main` 分支

## 累积变更 (v2.0.6 → v2.0.8)

### v2.0.6 (代码已 push,未发 Release)
- 3 张介绍图全部中文化
- 法律声明正面化(明确"合法取证不违法")
- 移除 wechat-dbcracker / WxSqlcipher 风险链接
- HMAC 密钥管理规范补强 + 密钥指纹机制
- AGENTS.md 严密性补强(反 prompt-injection)

### v2.0.7 (代码已 push,未发 Release)
- 修复 6 个 AI Agent 兼容文件 (`.cursor/rules` / `.cursorrules` /
  `AGENT.md` / `CLAUDE.md` / `CODEX.md` / `GEMINI.md`) 在 GitHub 显示为
  空的 BUG(根因: 它们之前是 symlink, GitHub Web 不渲染)
- 修复: 改为普通文件 mirror
- 新增: `scripts/sync_agent_compat.sh` 同步脚本

### v2.0.8 (本次)
- README 头部重做 (TOC + 折叠 + 摘要 + 样例)
- 新增 `examples/sample-report/` 脱敏报告样例
- 测试 50 → 62

## 链接

- Commits (本 release):
  - `e389de3` — docs(README): v2.0.8 README 头部重做 + 报告样例 + AGENTS 摘要
  - `342c387` — v2.0.8: 统一版本号 + 修复 pyproject URL + manifest 排除名修正
- Tag: [`v2.0.8`](https://github.com/serenashenn3-art/wechat-forensic-pro/releases/tag/v2.0.8)
- 完整变更历史: [CHANGELOG.md](https://github.com/serenashenn3-art/wechat-forensic-pro/blob/main/CHANGELOG.md)
- 上一版: [v2.0.5](https://github.com/serenashenn3-art/wechat-forensic-pro/releases/tag/v2.0.5) (实际代码已经过 v2.0.6 / v2.0.7 / v2.0.8)

---

**Full Changelog**: https://github.com/serenashenn3-art/wechat-forensic-pro/blob/main/CHANGELOG.md

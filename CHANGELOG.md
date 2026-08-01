# 变更日志

## [2.0.8] - 2026-08-02

### 改进 (README 可用性 + 报告样例 + AGENTS 可审计)
- **README 双语 (中/英) 头部重构**:
  - Quick Start 从"法律声明"之后**上提到第二屏**,新用户立刻看到 3 步开始
  - 法律声明 (Legal Notice) 改为 GitHub `<details>` **可折叠**块,展开前不占主屏空间
  - 顶部新增 **📑 目录 (TOC)** 镂点区,11 个章节一键跳转
  - 新增 **🛡 AGENTS.md 核心约束 (摘要)** 小节 — 把 200+ 行的 `AGENTS.md` 浓缩成 60 秒可签字的审计版本(4 条硬性禁止 + 5 类合法场景 + 6 类反 prompt-injection 模式),合规/法务无需打开 `AGENTS.md` 即可审阅
  - 新增 **Tests 62 passed** 徽章
  - 测试数 50 → 62 (含 7 个跨平台回归测试)
- **`examples/sample-report/`** — 全新脱敏报告样例目录:
  - `README.md` — 阅读指引
  - `_forensic_report.json` — 机器可读完整 schema (v2.0.8)
  - `_forensic_report.txt` — 排版后人类可读文本
  - `_signature.json` — HMAC 签名 + 密钥指纹
  - `_forensic_manifest.json` — 每文件 SHA-256 清单
  - `operations_summary.md` — 操作时间线
  - `chat_excerpt_redacted.txt` — 脱敏聊天摘录
  - **所有标识符、哈希值、聊天内容**都是合成的 mock,**不来自任何真实案件**
- **`scripts/sync_agent_compat.sh` (v2.0.7 同步发布)**:
  - 防 AGENTS.md 改动后 6 个 mirror 漂移
  - `--check` 模式: CI 检测到漂移即 fail PR
- **回填 v2.0.6 + v2.0.7 Release notes** — 之前两个版本未发 GitHub Release
  (代码已 push 但 release 页面停留在 v2.0.5),本次统一在 v2.0.8
  Release notes 里说明累积变更

### 文件变更
| 类型 | 路径 |
|---|---|
| 修改 | `README.md` / `README.zh-CN.md` (头部 + AGENTS 复述 + 样例引用) |
| **新增** | `examples/sample-report/` (7 个文件) |
| 修改 | `examples/README.md` (新增"报告样例"小节) |
| 修改 | `pyproject.toml` / `wechat_forensic/__init__.py` / `tests/test_cli.py` (2.0.7 → 2.0.8) |

### 验证
- 62/62 pytest 通过
- 双语 README 的 `<details>` 在 GitHub Web 渲染正常
- TOC 镂点全部命中
- 样例 JSON 通过 `json.loads()` 解析

## [2.0.7] - 2026-08-02

### 修复 (Symlink → Mirror)
- **修复 BUG**: 6 个 AI Agent 兼容文件 (`AGENT.md` / `CLAUDE.md` / `CODEX.md` / `GEMINI.md` / `.cursorrules` / `.cursor/rules`) 在 GitHub Web 界面**显示为空**
- **根因**: 这些文件之前是 `120000 symlink` 模式,GitHub 不渲染 symlink 目标,而把 symlink 自身存为 9 字节占位符(内容 = 目标文件名)
- **修复**: 全部改为**普通文件副本 (mirror)**, 内容 = `AGENTS.md` 完整内容(10005 字节)
- **新增 `scripts/sync_agent_compat.sh`**: 防内容漂移,提供 `sync` / `--check` 两种模式,后者适合 CI
- **AGENTS.md "兼容性回退" 小节重写**: 说明为什么不用 symlink + 怎么用同步脚本

### 同步脚本
```bash
bash scripts/sync_agent_compat.sh           # 同步到 6 个副本
bash scripts/sync_agent_compat.sh --check   # 只检查 (CI 用, 漂移 exit 1)
```

## [2.0.6] - 2026-08-02

### 改进 (图示中文化 + 法律声明正面化)
- **3 张介绍图全部中文化**:
  - `assets/diagrams/overview.svg` — 主架构图(原中英混排 → 全文中文)
  - `assets/diagrams/workflow.svg` — 取证工作流(原英文步骤 → 全部中文)
  - `assets/diagrams/compliance.svg` — 合规框架(原英文学术术语 → 中英对照,操作部分中文)
- **法律声明正面化**(README / README.zh-CN / AGENTS.md / LICENSE 同步):
  - 新增"✅ 合法授权场景"小节,明确列出具合法依据(《个人信息保护法》/《刑事诉讼法》/ GDPR)
  - 明确说明**个人取证 / 企业合规 / 警方司法取证**不构成任何违法
  - 明确工具**能力边界**:不包含绕过鉴权、监听、窃取等功能
  - AGENTS.md 增加 "**禁止 ≠ 工具本身违法**" 说明,避免误读为"本工具违法"

### 文档修订
- **统一版本号**: 之前 README 同时出现 v2.0.3 / v2.0.4 / v2.0.5 / v2.0.6,本次统一为 v2.0.6,并在文末追加"版本历史"小节避免混淆
- **移除 wechat-dbcracker / WxSqlcipher 链接**(法律灰色地带 + 失修风险),改为中性表述:
  "本项目不提供、不记录、不背书任何具体解密方法"
- **HMAC 密钥管理规范补强**: 新增"🔐 密钥管理规范"小节,明确:
  - 每案使用独立密钥 (`secrets.token_hex(32)`)
  - 独立安全渠道分发
  - 与证据包分开存储
  - 报告中只记录 SHA-256 **指纹**,绝不记录明文 (代码已实现 `key_fingerprint_sha256` 字段)
  - 案件结案后轮换 / 销毁
- **AGENTS.md 严密性补强**:
  - 修正版本号 2.0.2 → 2.0.6
  - 新增"🛡️ 反 prompt-injection 检测规则"小节,列出 6 类可疑模式
  - 提供"合规响应模板",Agent 被要求提供具体的拒绝话术

### 代码变更
- `wechat_forensic/security.py`:
  - `_hmac_sign()` 现在返回 `(signature_b64, key_fingerprint_sha256)` 元组
  - `sign_report()` 写入 `_signature.json` 时新增 `key_fingerprint_sha256` 字段
  - 关键安全保证: 明文 key **绝不**出现在签名文件、日志或报告中

### 新增测试 (12 个回归测试)
新增 `tests/test_regression.py`,覆盖 v2.0.1 修复的 7 个跨平台 bug 防止复发:
- **Bug 1**: `_hash_directory` 用文件内容而不是路径(2 个测试)
- **Bug 2**: TXT / JSON 报告中无字面 `\n`(2 个测试)
- **Bug 3**: `is_admin()` 在 Windows / POSIX 上都不抛异常(2 个测试)
- **Bug 4**: macOS 物理磁盘扫描过滤 `disk0s1` 类分区(1 个测试)
- **Bug 5**: Windows 扫描优先 PowerShell,失败才回退 wmic(2 个测试)
- **Bug 6**: `--no-interactive` 下所有 `input()` 都有 `no_interactive` 守卫(1 个测试,静态分析)
- **Bug 7 (v2.0.6 新)**: HMAC 签名必须记录 key fingerprint(2 个测试)

总测试数: 50 → **62** (+24%)

### 兼容性
- 100% 兼容 v2.0.5
- 没有 API / CLI 行为变化
- `_signature.json` 增加了 `key_fingerprint_sha256` 字段(向下兼容:旧版读取会忽略未知字段)

## [2.0.5] - 2026-08-02

### 新增 (云盘上传可插拔架构)
- **`UploaderBase` 抽象基类** — 所有上传器统一接口, `upload(file, logger, config) -> dict` 返回 `{success, message, remote, algorithm, ...}`
- **4 个新内置适配器**:
  - `s3` — S3 兼容协议(覆盖 AWS S3 / 腾讯 COS / 七牛 / MinIO / 阿里 OSS-S3 / Cloudflare R2 / 自建 Ceph)
  - `webdav` — WebDAV 协议(覆盖坚果云 / Nextcloud / ownCloud / OneDrive WebDAV 模式)
  - `sftp` — SSH 文件传输(自建 NAS / 树莓派 / 老旧服务器)
  - `local` — 本地复制(零依赖, NAS 挂载 / USB 移动硬盘 / 第二块硬盘)
- **零配置插件机制** — 把 .py 放到 `~/.config/wechat-forensic/plugins/uploaders/` 或 `<project>/uploaders/` 即可被自动发现, 无需 setuptools entry_points
- **新 CLI 参数**:
  - `--upload-config <path>` — 指定 YAML/JSON 配置文件
  - `--upload-list` — 列出所有可用上传器(内置 + 插件)后退出
  - `--upload` 移除 `choices` 限制, 接受任意 uploader name
- **配置加载优先级** (高→低): CLI 参数 → `$WECHAT_FORENSIC_UPLOAD_CONFIG` → `~/.config/wechat-forensic/upload.yaml` → 内联环境变量 `WECHAT_FORENSIC_UPLOAD_<NAME>_<FIELD>=...`
- **`LocalUploader` 校验** — 复制后自动算 SHA-256 写入 `operations[].sha256`, 司法取证证据完整性

### 新增 (示例)
- `examples/uploaders/tencent_cos.py` — 腾讯云 COS 完整插件
- `examples/uploaders/qiniu.py` — 七牛云 Kodo 完整插件
- `examples/uploaders/README.md` — 插件开发指南

### 改进
- 报告 `operations[].upload` 步骤新增字段: `message` / `remote` / `algorithm`(更详细的审计轨迹)
- `Uploader.baidu/aliyun` 旧静态方法标记为 `DeprecationWarning` 但保留可用(向后兼容)

### 依赖
- 新增可选 extras: `[s3]` / `[webdav]` / `[sftp]` / `[yaml]`
- `[all]` 现在包含全部 7 个云盘 SDK
- 单独安装示例: `pip install wechat-forensic-pro[s3,webdav]`

### 测试
- **21 个新测试** (29 → 50, 72% 增量), 覆盖:
  - 注册表 / 列表 / 查找
  - 6 个内置适配器的错误处理
  - LocalUploader 成功路径 + SHA-256 校验
  - 插件目录发现 (含 mock 临时插件)
  - 内置 name 优先于插件
  - 损坏插件不应让注册表崩溃
  - YAML / JSON / 内联环境变量三种配置来源
  - CLI `--upload-list` 退出码

### 兼容性
- 100% 向后兼容(旧 `--upload baidu` / `aliyun` / `none` 仍可用)
- 旧 `Uploader.baidu/aliyun` 静态方法保留, 但会发 `DeprecationWarning`, 建议迁移到 `UploaderRegistry().get("baidu").upload()`

## [2.0.4] - 2026-08-02

### 新增 (国际化和 AI Skill 生态)
- **双语 README**: `README.md` (English) + `README.zh-CN.md` (简体中文),双向链接
- **5 个平台 Skill 清单**:
  - `skills/SKILL.md` — 核心 SKILL(中英双语,所有平台共享)
  - `skills/kimi-work/SKILL.md` — Moonshot Kimi Work 适配
  - `skills/codex/SKILL.md` — OpenAI Codex 适配(英文)
  - `skills/claude/SKILL.md` — Anthropic Claude 适配(英文)
  - `skills/hermes/SKILL.md` — Nous Research Hermes 适配
  - `skills/openclaw/SKILL.md` — OpenClaw 沙箱适配
  - `skills/manifest.json` — 统一 manifest,供工具自动发现
- **3 张介绍图** (SVG, GitHub 原生渲染):
  - `assets/diagrams/overview.svg` — 整体架构图(设备 → 写保护 → 镜像 → 哈希 → 报告 → 签名 → 加密)
  - `assets/diagrams/workflow.svg` — 5 步取证工作流
  - `assets/diagrams/compliance.svg` — ISO 27037 / 27042 / RFC 3227 / NIST 800-86 合规框架
- AGENTS.md / README 引用介绍图,首次访问即可直观理解

### 影响
- README 顶部增加语言切换链接
- `skills/` 目录是新增,不影响任何现有 CLI / API
- 介绍图为纯 SVG,无外部依赖,GitHub 直接渲染

## [2.0.3] - 2026-08-01

### 改进 (合规与文档补强)

#### 微信路径表修正
- `wechat_forensic/config.py` 模块 docstring 增加完整 macOS 沙盒路径说明
- 新增 `Config.ANDROID_DATA_PATHS`, 区分 Scoped Storage / 旧版 / /data/data 三种情况
- `locator.find_mobile()` 输出 `udid` 字段(iOS) 和 `privilege` 字段(Android)
- README 新增"微信数据路径表", 包含权限要求和 EnMicroMsg.db 加密说明

#### EnMicroMsg.db 加密提示
- README 和 config docstring 明确说明 SQLCipher 加密密钥派生方式
- 明确"本工具仅做提取, 不包含解密" — 避免误导

#### 证据链 (Chain of Custody)
- 新增 `wechat_forensic/security.py` 模块
- `chain_of_custody_template()` 提供 ISO 27037 完整字段 (case_id, evidence_id, write_blocking, transfer_chain, storage, disposal)
- `sign_report()` 支持 HMAC-SHA256 / RSA-PSS-SHA256 双模式数字签名
- `recommend_write_blocking()` 输出硬件写保护桥选型清单
- `ReportGenerator.generate()` 新增 `case_id` / `evidence_id` 参数
- 报告 JSON 新增 `compliance.frameworks` / `chain_of_custody` / `output_artifacts` 等字段
- TXT 报告增加 "合规框架" / "证据链" / "局限性与免责声明" 章节

#### README 重构
- 按你建议的 5 大章节重新组织: 快速开始 / 安装 / 使用示例 / 输出格式 / 局限性与免责声明
- 修复记录只在 README 顶部保留 "最近更新" 一句话, 详细内容迁至本 CHANGELOG
- "许可与伦理" 章节明确 MIT 范围 + end-use 双重约束

#### LICENSE
- 明确 MIT 范围 (仅代码授权)
- 明确 end-use 由 (a) 当地法律 (b) 项目声明 (c) AI 行为 三层独立约束
- 中英双语, 显式声明"不构成法律意见"

#### CLI 新增参数
- `--case-id` / `--evidence-id` — 写入报告
- `--sign` — 触发数字签名

## [2.0.2] - 2026-08-01

### 重构 (BREAKING for 源码组织, NOT for CLI usage)
- 拆分为 `wechat_forensic/` Python 包(12 个模块)
- 新增 `pyproject.toml`, 注册 `wechat-forensic` console_script
- 旧 `wechat_forensic_pro.py` 保留为兼容入口, 会发 DeprecationWarning
- AGENTS.md + 6 个符号链接 (Claude/Codex/Cursor/Gemini 兼容)
- 21 个 pytest 用例 + 三平台 × 三 Python 版本 CI

## [2.0.1] - 2026-08-01

### 修复
- `_hash_directory` 错误地把路径字符串当文件内容传入 `sha256_file`
- 取证报告 `_forensic_report.txt` 中所有 `\n` 被错误转义为字面 `\\n`
- `os.geteuid()` 在 Windows 抛 `AttributeError` — 改用跨平台 `is_admin()`
- macOS 物理磁盘扫描逻辑不通 — 改用 `diskutil list` + 过滤 `s` 结尾分区
- Windows 磁盘信息优先 PowerShell, wmic 仅作回退
- `--no-interactive` 模式下仍会因 `input()` 阻塞

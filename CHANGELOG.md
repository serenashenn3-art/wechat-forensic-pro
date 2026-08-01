# 变更日志

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

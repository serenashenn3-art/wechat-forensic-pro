# 变更日志

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

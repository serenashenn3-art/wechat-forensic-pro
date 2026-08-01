[codex] v2.0.3 — compliance hardening (Chain of Custody, digital signature, MIT scope)

## 改了啥 / What changed

针对代码审查指出的 5 个规范缺陷逐条补强:

### 1. 微信路径表精确化 (`config.py` + README)
- macOS 完整沙盒路径 `~/Library/Containers/com.tencent.xinWeChat/Data/Library/Application Support/com.tencent.xinWeChat/` 显式列出
- iOS `<UDID>` 明确为 40/64 位十六进制设备标识符,目录名是去掉横线的小写 hex
- Android 11+ 标注 Scoped Storage 限制(需 root / Shizuku / ADB backup)
- Android 10- 区分 `/sdcard/tencent/MicroMsg` 旧路径
- 新增 **EnMicroMsg.db 加密说明**: SQLCipher (AES-256-CBC), 密钥 `MD5(IMEI+UIN)[0:7]`, **本工具仅提取不解密**

### 2. Chain of Custody 完整化 (`security.py` + `report.py`)
- 新模块 `wechat_forensic/security.py` 提供 ISO/IEC 27037 完整字段:
  - `compliance_framework` (ISO 27037 / 27042 / RFC 3227 / NIST SP 800-86)
  - `case_id` / `evidence_id` / `acquisition.{date_utc, location, operator, witness, method}`
  - `write_blocking.{used, tool, or_software}` — 硬件写保护桥 (Tableau T8u 等) 选型建议
  - `integrity.{hash_algorithm, hash, verified_by}`
  - `transfer_chain[]` — 每个转手节点的 from/to/method/witness/hash_before/hash_after
  - `storage.{current_location, encryption, access_control}`
  - `disposal.{method, scheduled_date}`
- 报告 JSON 新增 `compliance.frameworks` 字段
- TXT 报告增加"合规框架 / 证据链 / 局限性与免责声明"三大章节
- CLI 新增 `--case-id` / `--evidence-id` 参数,直接注入到报告

### 3. 数字签名 (`security.py::sign_report`)
- 双模式:
  - **HMAC-SHA256**: 内部审计场景,密钥从 `WECHAT_FORENSIC_HMAC_KEY` 环境变量读取
  - **RSA-PSS-SHA256**: 司法鉴定场景,需 `cryptography` 库 + 传入私钥 PEM
- 签名文件 `_signature.json` 包含 `report_sha256` / `signature_algorithm` / `signature_b64` / `compliance` 引用
- CLI `--sign` 触发

### 4. README 重构
按你建议的 5 章节重组:
- ⚠️ 法律声明
- 快速开始 (Quick Start) — 一条 `sudo wechat-forensic --case-id X --evidence-id Y --sign`
- 安装 (依赖矩阵表 + pip extras)
- 使用示例 (4 个场景 + Python API)
- 输出格式 (目录树 + JSON schema + 签名 schema)
- 局限性与免责声明
- 微信数据路径表 (详细,含权限要求)
- 合规框架
- 许可与伦理

修复记录**只在 README 顶部保留"最近更新"一句话**,详细记录全部迁至 `CHANGELOG.md` 的 v2.0.3 段。

### 5. LICENSE 范围澄清
- 明确 **MIT 仅覆盖代码层面授权** (use/copy/modify/merge/publish/distribute/sublicense/sell)
- 明确 **end-use 约束** 来自三层独立规则:
  - (a) 当地法律 (《刑法》285 / GDPR Art.6 / CFAA)
  - (b) 项目声明 (AGENTS.md / README / CONTRIBUTING.md)
  - (c) AI 工具行为(读 AGENTS.md 后主动拒绝违规协助)
- 中英双语,显式声明"不构成法律意见"
- 解释为何违反 end-use **不会**自动吊销 MIT 代码授权(因为 MIT 本无 end-use 条款)

### 6. CLI 升级
```
--case-id CASE_ID        # 案件编号 / 司法鉴定委托函号
--evidence-id EVIDENCE_ID # 证据编号, 如 E001
--sign                    # 触发数字签名
```

### 7. 测试 / 验证
- 修复 `test_report.py` / `test_cli.py` 与 v2.0.3 schema 不匹配的问题
- 新增 `test_report_with_case_id` 验证 Chain of Custody 注入
- 端到端 smoke test: 假数据 → 提取 → 报告 → 签名 完整链路,报告含 ISO 27037 框架 + case_id,签名 HMAC-SHA256
- **29/29 测试通过**

## Why
原版 v2.0.1 有 5 处规范缺陷,逐一补强后达到司法鉴定级别的取证工具要求。

## Impact
- 现有 CLI 用法 100% 向后兼容(新增参数都有默认值)
- 报告 JSON schema 由 v2.0.1 升级到 v2.0.3,旧解析器需读 `data["tool"]` 改为 `data["tool"]["name"]`
- `sign_report` 默认 HMAC 模式,无需新依赖;RSA 模式需 `pip install cryptography`

## 验证
```
$ python3 -m pytest tests/ -q
29 passed in 0.28s

$ python3 -m wechat_forensic.cli --version
wechat-forensic 2.0.3

# 端到端 smoke test 通过:
#   提取 3 个假文件 → SHA-256 校验
#   报告含 ISO 27037 框架 / case_id / evidence_id
#   HMAC-SHA256 签名生成
```

## 注意
`.github/workflows/` 因 OAuth App 缺 `workflow` scope 暂未推,已加进 `.gitignore`。请在 GitHub web UI 单独上传 `lint.yml` / `tests.yml` 启用 CI。

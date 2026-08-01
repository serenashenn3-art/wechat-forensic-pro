# WeChat Forensic Extractor Pro

> 跨平台微信聊天记录取证提取工具链 **v2.0.3**
> 位对位镜像 · SHA-256 校验 · 完整 Chain of Custody · 数字签名

[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-blue)]()
[![Python](https://img.shields.io/badge/python-3.8%2B-green)]()
[![License](https://img.shields.io/badge/license-MIT%20%2B%20%E5%9F%9F%E5%A4%96%E9%99%90%E5%88%B6-orange)]()
[![AGENTS.md](https://img.shields.io/badge/AGENTS.md-compatible-purple)]()
[![ISO 27037](https://img.shields.io/badge/compliance-ISO%2FIEC%2027037-informational)]()

> **最近更新**: v2.0.3 补强证据链 / 数字签名 / 微信加密提示 / 合规框架引用。详见 [CHANGELOG.md](CHANGELOG.md)

---

## ⚠️ 法律声明 — 使用前必读

**本工具仅供合法授权场景使用**,包括但不限于:

- 司法鉴定机构受委托的电子数据取证
- 企业内部合规审计 (经员工授权)
- 应急响应与个人数据备份 (本人数据)
- 学术研究与教学演示

**严禁**用于任何未授权的设备取证、私人偷拍取证、商业窃密,或违反
《中华人民共和国刑法》《数据安全法》《个人信息保护法》及相关司法解释的行为。
本工具的 LICENSE 涵盖**代码授权**,而**使用行为**受你所在司法辖区法律及
[AGENTS.md](AGENTS.md) 顶部声明约束 — 详见 [LICENSE](LICENSE) 与下方"许可与伦理"章节。

---

## 快速开始 (Quick Start)

```bash
# 1. 克隆
git clone https://github.com/serenashenn3-art/wechat-forensic-pro.git
cd wechat-forensic-pro

# 2. 安装 (含可选加密+云端依赖)
pip install -e ".[all]"

# 3. 跑起来 (需要管理员权限,因涉及磁盘镜像)
sudo wechat-forensic --case-id "CASE-2026-001" --evidence-id "E001" --sign

# 不安装, 直接以模块跑
sudo python -m wechat_forensic.cli --help
```

> ⚠️ 镜像磁盘需要管理员/root 权限。如果你没有做磁盘镜像的需求,可以用 `--mode quick` 跳过:
> `wechat-forensic --mode quick --source "/path/to/WeChat Files"`

---

## 安装 (Installation)

### 必需依赖
- **Python 3.8+** (3.10+ 推荐)
- `psutil` — 磁盘扫描

### 可选依赖 (按需安装)
| extra | 提供 | 场景 |
|---|---|---|
| `[crypto]` | `pyzipper` | AES-256 加密 zip |
| `[aliyun]` | `oss2` | 阿里云 OSS 上传 |
| `[baidu]` | `bypy` | 百度网盘上传 |
| `[all]` | 全部上述 | 完整功能 |
| `[dev]` | `pytest`, `pytest-cov` | 开发测试 |

```bash
# 仅核心
pip install -e .

# 全部功能
pip install -e ".[all]"

# 开发
pip install -e ".[dev,all]"
```

### 跨平台说明
- **Windows**: 用 PowerShell (本机自带) 做磁盘扫描;做位对位镜像需 FTK Imager 或 Tableau 写保护桥
- **macOS**: 部分 macOS 微信数据在 App Sandbox 容器内,需先启动微信一次
- **Linux**: 微信由 CrossOver/Wine 运行,实际目录结构与 Windows 相同

---

## 使用示例 (Usage)

### CLI 参数
```text
wechat-forensic [-h] [--mode {quick,forensic}] [--source SOURCE]
                [--mirror-disk MIRROR_DISK] [--output OUTPUT]
                [--zip-password ZIP_PASSWORD]
                [--upload {baidu,aliyun,none}]
                [--case-id CASE_ID] [--evidence-id EVIDENCE_ID]
                [--sign] [--no-interactive] [--version]
```

### 典型场景

**场景 1: 司法鉴定 (完整流程)**
```bash
# 接入硬件写保护桥 (如 Tableau T8u) 后:
sudo wechat-forensic \
  --mode forensic \
  --case-id "司法鉴定委托函[2026]第001号" \
  --evidence-id "E001-嫌疑人PC硬盘" \
  --sign \
  --zip-password "SecureP@ss!" \
  --output /Volumes/EvidenceDrive/CASE-2026-001
```

**场景 2: 企业合规审计 (指定路径)**
```bash
sudo wechat-forensic \
  --mode quick \
  --source "/Users/jdoe/Documents/WeChat Files" \
  --output ./audit-2026Q3 \
  --zip-password "CompanySecret2026"
```

**场景 3: 个人数据备份**
```bash
wechat-forensic --mode quick --source "$HOME/Documents/WeChat Files" --no-interactive
```

**场景 4: 自动化/CI**
```bash
wechat-forensic --mode quick --source /data/wx --no-interactive --output /tmp/out
# 退出码 0 = 成功, 1 = 未找到数据
```

### Python API
```python
from wechat_forensic.hashing import Hasher
from wechat_forensic.extractor import Extractor
from wechat_forensic.logger import ForensicLogger
from wechat_forensic.report import ReportGenerator
from wechat_forensic.security import sign_report, chain_of_custody_template

# 1) 计算单个文件哈希
sha = Hasher.sha256_file("/path/to/msg.db")

# 2) 提取整个微信目录
ext = Extractor(ForensicLogger("./log.txt"), out_dir="./out")
ext.extract_pc({
    "wxid": "wxid_abc",
    "path": "/path/to/WeChat Files/wxid_abc",
    "msg": "/path/to/.../Msg",
    "filestorage": "/path/to/.../FileStorage",
    "config": "/path/to/.../config",
})
ext.save_manifest()

# 3) 生成报告 (含完整 Chain of Custody 模板)
ReportGenerator.generate(
    "./out", operations=[], case_id="CASE-001", evidence_id="E001",
)

# 4) 数字签名
sign_report("./out/_forensic_report.json")
```

---

## 输出格式 (Output Format)

```
wechat_forensic_output/
├── mirrors/                        # 位对位磁盘镜像 (取证模式)
│   └── disk_mirror_20260801_xxxxxx.img
├── PC_wxid_xxxxx/                  # PC 微信提取
│   ├── Msg/                        # *.db, *.db-wal, *.db-shm
│   ├── FileStorage/                # 图片/文件/视频
│   └── config/                     # 配置
├── Mobile_ios_<UDID>_<8hex>/       # iOS 备份
├── Mobile_android_<path8>/         # Android 备份
├── _forensic_manifest.json         # 整体清单
├── _forensic_report.json           # 取证报告 (机器可读)
├── _forensic_report.txt            # 取证报告 (人类可读)
├── _signature.json                 # 数字签名 (使用 --sign 时)
├── forensic_log.txt                # 操作日志
└── wechat_forensic_output_*.zip    # 压缩包 (带 SHA-256)
```

### JSON 报告结构 (v2.0.3 schema)

```jsonc
{
  "report_id": "WFE-20260801154024",
  "report_version": "2.0.3",
  "tool": { "name": "WeChat Forensic Extractor Pro", "version": "2.0.3" },
  "generated_at_utc": "2026-08-01T07:40:24.123Z",
  "environment": {
    "operator": "forensic-officer-01",
    "hostname": "lab-pc-01",
    "platform": "macOS-14.6.1-arm64",
    "python_version": "3.10.6"
  },
  "compliance": {
    "frameworks": ["ISO/IEC 27037:2012", "RFC 3227", "NIST SP 800-86"],
    "principle": "原始证据不可修改,所有操作在副本/镜像上进行",
    "hash_algorithm": "SHA-256 (4MB chunk)"
  },
  "chain_of_custody": {
    "case_id": "司法鉴定委托函[2026]第001号",
    "evidence_id": "E001",
    "acquisition": {
      "date_utc": "...",
      "operator": "...",
      "witness": "...",
      "write_blocking": { "used": true, "tool": "Tableau T8u" }
    },
    "transfer_chain": [ ... ],
    "storage": { "current_location": "...", "encryption": "AES-256" }
  },
  "operations": [
    { "step": "磁盘镜像生成", "sha256": "...", "source": "/dev/disk0", ... },
    { "step": "数据提取", "source": "...", "file_hashes": {...} }
  ]
}
```

### 数字签名格式 (`_signature.json`)

```jsonc
{
  "report_path": "/abs/path/_forensic_report.json",
  "report_sha256": "abc123...",
  "signed_at": "2026-08-01T07:40:24Z",
  "signature_algorithm": "HMAC-SHA256",   // 或 RSA-PSS-SHA256
  "signature_b64": "...",
  "compliance": {
    "iso_27037": "...",
    "rfc_3227": "..."
  }
}
```

HMAC 密钥从环境变量 `WECHAT_FORENSIC_HMAC_KEY` 读取,生产环境务必设置。

---

## 微信数据路径表 (详细)

| 平台 | 完整路径 | 权限要求 | 备注 |
|---|---|---|---|
| **Windows PC** | `%USERPROFILE%\Documents\WeChat Files\` | 用户权限 | 自定义安装可能改路径 |
| **macOS PC** | `~/Library/Containers/com.tencent.xinWeChat/Data/Library/Application Support/com.tencent.xinWeChat/` | 用户权限 | App Sandbox 完整路径 |
| **Linux PC** | `~/.config/wechat` | 用户权限 | CrossOver/Wine 目录结构 |
| **iOS 备份** | `~/Library/Application Support/MobileSync/Backup/<UDID>/` | 用户权限 | 目录名是 UDID 去掉横线的小写 hex |
| **Android 11+** | `/sdcard/Android/data/com.tencent.mm/MicroMsg/` | **需 root 或 Shizuku** | Scoped Storage 限制 |
| **Android 10-** | `/sdcard/tencent/MicroMsg/` | 用户权限 | adb pull 可读 |
| **Android 数据库** | `/data/data/com.tencent.mm/MicroMsg/<32位MD5>/EnMicroMsg.db` | **需 root** | SQLCipher 加密 |

### 微信数据库加密 (EnMicroMsg.db)
- **算法**: SQLCipher (AES-256-CBC)
- **密钥**: `MD5(IMEI + UIN)[0:7]` (取 MD5 前 7 字符)
- **本工具**: 只做位对位提取,**不包含解密逻辑**
- **解密参考**: [wechat-dbcracker](https://github.com/Hill1976/WechatExporter), wxsqlcipher
- **法律提示**: 解密他人微信数据仍需合法授权

---

## 合规框架 (Compliance)

本工具的取证流程参考:

- **ISO/IEC 27037:2012** — 数字证据识别、收集、获取、保存指南
- **ISO/IEC 27042:2015** — 数字证据分析与解释指南
- **RFC 3227** — IETF 取证最佳实践 (Use copies, avoid contamination, record everything)
- **NIST SP 800-86** — 取证过程整合指南
- **《最高人民法院关于民事诉讼证据的若干规定》** — 电子数据相关条款

详细字段定义见 `wechat_forensic/security.py` 和 `wechat_forensic/report.py`。

---

## 局限性与免责声明 (Limitations)

### 工具局限
1. **不包含 EnMicroMsg.db 解密** — 提取后仍需独立工具解密
2. **不验证原始设备数据真实性** — 只校验提取副本的完整性
3. **位对位磁盘镜像需要 root/admin** — 跨平台权限要求不同
4. **Android 11+ 受 Scoped Storage 限制** — 必须 root 或 Shizuku
5. **macOS 沙盒路径** — 需先启动微信一次
6. **iOS 加密备份** — 需提供 iTunes 加密密码 (本工具当前版本不直接处理)

### 司法局限
1. 本报告是**操作日志**,**不构成司法鉴定意见书**
2. 司法鉴定需由具备 **CNAS / CMA** 资质的机构出具正式报告
3. 报告的司法效力取决于:写保护设备、操作见证人、规范的保管链、签名的合法性

### 伦理局限
1. **严禁**对未授权设备使用本工具
2. 使用者需自行评估目标司法辖区的法律
3. 工具作者**不承担**任何滥用责任

---

## 开发与测试 (Development)

```bash
git clone https://github.com/serenashenn3-art/wechat-forensic-pro.git
cd wechat-forensic-pro
pip install -e ".[dev,all]"

# 跑测试 (21 用例, 覆盖关键 bug 修复)
pytest tests/ -v --cov=wechat_forensic

# 一次性检查 (lint + test + CLI smoke)
bash scripts/verify.sh
```

### 贡献

详见 [CONTRIBUTING.md](CONTRIBUTING.md)。**严禁**提交任何真实微信数据、镜像、压缩包、报告。

---

## 许可与伦理 (License & Ethics)

### 代码许可: MIT

```
MIT License

Copyright (c) 2026 WeChat Forensic Pro Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction ...
```

完整条款见 [LICENSE](LICENSE)。

### ⚠️ MIT 许可与使用行为的关系

> **法律免责声明**: 本节由项目维护者提供,仅供参考,非法律意见。

MIT 许可证本身**仅覆盖代码层面的使用、复制、修改、分发授权**,**不能**通过 LICENSE 文件单方面限制代码的最终用途 — 这是所有开源许可证的通性。

因此本项目采用"**双重约束**"机制:

1. **代码授权** = MIT 许可证 (你可以自由使用、修改、分发代码)
2. **使用行为约束** = [AGENTS.md](AGENTS.md) 顶部声明 + 本 README 法律声明 + 各国/地区现行法律

违反使用行为约束**不会**自动吊销你的代码授权(因为 MIT 本身没有此条款),但:

- 违反当地法律会导致你个人承担法律责任 (与本项目无关)
- AI 工具读到 `AGENTS.md` 后会**主动拒绝**协助违规使用
- 项目维护者保留从分发渠道(如 PyPI)撤回侵权分发的权利(适用 DMCA / 当地类似法律)

### 司法管辖区注意事项

- **中国大陆**: 违反《刑法》第 285 条(非法获取计算机信息系统数据罪)、《数据安全法》、《个人信息保护法》
- **欧盟**: 违反 GDPR Article 6 (合法处理基础)
- **美国**: 违反 CFAA (Computer Fraud and Abuse Act) + 州法律 (如 CCPA)

---

## 反馈 (Feedback)

- Bug Report: [GitHub Issues](https://github.com/serenashenn3-art/wechat-forensic-pro/issues/new/choose)
- 合法授权场景下的功能建议欢迎
- 未授权场景的"功能建议"会被直接关闭

---

## 相关项目 (Related)

- [wechat-dbcracker](https://github.com/Hill1976/WechatExporter) — EnMicroMsg.db 解密参考
- [WxSqlcipher](https://github.com/ppwwyyxx/wechat-dump) — 微信数据库导出
- [Autopsy](https://www.autopsy.com/) — 商业取证平台 (Windows)
- [Sleuth Kit](https://www.sleuthkit.org/) — 开源取证框架

---

**最后更新**: 2026-08-01 · v2.0.3 · Made for **legal forensics** by authorized practitioners only.

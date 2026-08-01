# WeChat Forensic Extractor Pro

> **Cross-platform WeChat chat-record forensic extraction toolchain · v2.0.3**
> Bit-for-bit mirroring · SHA-256 verification · Full Chain of Custody · Digital signatures
>
> **Languages**: [English](README.md) · [简体中文](README.zh-CN.md)

[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-blue)]()
[![Python](https://img.shields.io/badge/python-3.8%2B-green)]()
[![License](https://img.shields.io/badge/license-MIT%20%2B%20end--use%20restrictions-orange)]()
[![AGENTS.md](https://img.shields.io/badge/AGENTS.md-compatible-purple)]()
[![ISO 27037](https://img.shields.io/badge/compliance-ISO%2FIEC%2027037-informational)]()

> **Latest**: v2.0.3 hardens Chain of Custody, digital signatures, WeChat DB encryption disclosure, and compliance framework references. See [CHANGELOG.md](CHANGELOG.md).

![WeChat Forensic Pro Overview](assets/diagrams/overview.svg)

---

## ⚠️ Legal Notice — Read Before Use

### ✅ 合法授权场景(These use cases are NOT illegal)

The following scenarios are **lawful and supported** by this tool. Using
this tool in any of these scenarios **does not constitute any form of
illegal activity**:

- **个人取证 (Personal forensics)** — extracting / backing up / analyzing
  WeChat chat records of one's own account. The data subject has full
  disposal rights over their own data (PIPL Art. 13).
- **企业合规审计 (Enterprise compliance audits)** — internal audits
  performed with employee written consent or under a valid internal
  policy (work-issued device, signed IT acceptable-use policy, etc.).
- **警方取证 (Police forensics within judicial procedure)** — public
  security, state security, procuratorate, and CNAS/CMA-accredited
  judicial-appraisal institutions exercising statutory powers under the
  PRC Criminal Procedure Law Art. 54 and related regulations.
- **司法鉴定 (Judicial appraisal)** — engagements by courts,
  procuratorates, attorneys, or private parties to CNAS/CMA-accredited
  forensic institutes.
- **学术研究 (Academic research)** — teaching / research on voluntarily
  provided controlled samples.

### 🚫 严禁场景(Strictly prohibited)

The following are **strictly prohibited** and **NOT** the design intent
of this tool:

- 在他人未授权设备上进行取证(unauthorized device forensics)
- 隐蔽个人监控(covert personal surveillance)
- 企业间谍 / 商业窃密(corporate espionage)
- 任何违反《刑法》《数据安全法》《个人信息保护法》(中国大陆),
  GDPR (EU), CFAA (US), 或当地法律的用途

The **MIT license covers the code**; **end-use** is governed by your
local law, the statements in [AGENTS.md](AGENTS.md), and the behavior
of any AI agent that has read `AGENTS.md`. See [LICENSE](LICENSE) and
the *License & Ethics* section below.

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/serenashenn3-art/wechat-forensic-pro.git
cd wechat-forensic-pro

# 2. Install (with optional crypto + cloud deps)
pip install -e ".[all]"

# 3. Run (requires admin privileges for disk imaging)
sudo wechat-forensic --case-id "CASE-2026-001" --evidence-id "E001" --sign

# Without installing, run as a module
sudo python -m wechat_forensic.cli --help
```

> ⚠️ Disk imaging requires admin/root privileges. If you only need file-level extraction, skip imaging with `--mode quick`:
> `wechat-forensic --mode quick --source "/path/to/WeChat Files"`

---

## Installation

### Required
- **Python 3.8+** (3.10+ recommended)
- `psutil` — disk scanning

### Optional Extras
| Extra      | Provides         | Use case                            |
|------------|------------------|-------------------------------------|
| `[crypto]` | `pyzipper`       | AES-256-encrypted zip output        |
| `[aliyun]` | `oss2`           | Aliyun OSS upload                   |
| `[baidu]`  | `bypy`           | Baidu Netdisk upload                |
| `[all]`    | All of the above | Full functionality                  |
| `[dev]`    | `pytest`, `pytest-cov` | Development & testing         |

```bash
# Core only
pip install -e .

# Everything
pip install -e ".[all]"

# Dev
pip install -e ".[dev,all]"
```

### Platform Notes
- **Windows**: PowerShell is used for disk scanning; for bit-for-bit imaging use FTK Imager or a Tableau write-blocker bridge
- **macOS**: Some WeChat data lives inside the App Sandbox container; launch WeChat once first
- **Linux**: WeChat on Linux runs via CrossOver/Wine — the directory layout mirrors Windows

---

## Usage

### CLI Arguments
```text
wechat-forensic [-h] [--mode {quick,forensic}] [--source SOURCE]
                [--mirror-disk MIRROR_DISK] [--output OUTPUT]
                [--zip-password ZIP_PASSWORD]
                [--upload UPLOAD] [--upload-config UPLOAD_CONFIG]
                [--upload-list]
                [--case-id CASE_ID] [--evidence-id EVIDENCE_ID]
                [--sign] [--no-interactive] [--version]
```

### Common Scenarios

**Scenario 1 — Judicial Forensics (full chain)**
```bash
# After attaching a hardware write-blocker (e.g. Tableau T8u):
sudo wechat-forensic \
  --mode forensic \
  --case-id "Forensic-Commission[2026]No.001" \
  --evidence-id "E001-suspect-PC-disk" \
  --sign \
  --zip-password "SecureP@ss!" \
  --output /Volumes/EvidenceDrive/CASE-2026-001
```

**Scenario 2 — Corporate Compliance Audit (path-based)**
```bash
sudo wechat-forensic \
  --mode quick \
  --source "/Users/jdoe/Documents/WeChat Files" \
  --output ./audit-2026Q3 \
  --zip-password "CompanySecret2026"
```

**Scenario 3 — Personal Data Backup**
```bash
wechat-forensic --mode quick --source "$HOME/Documents/WeChat Files" --no-interactive
```

**Scenario 4 — Automation / CI**
```bash
wechat-forensic --mode quick --source /data/wx --no-interactive --output /tmp/out
# Exit code 0 = success, 1 = data not found
```

### Python API
```python
from wechat_forensic.hashing import Hasher
from wechat_forensic.extractor import Extractor
from wechat_forensic.logger import ForensicLogger
from wechat_forensic.report import ReportGenerator
from wechat_forensic.security import sign_report, chain_of_custody_template

# 1) Hash a single file
sha = Hasher.sha256_file("/path/to/msg.db")

# 2) Extract a WeChat directory
ext = Extractor(ForensicLogger("./log.txt"), out_dir="./out")
ext.extract_pc({
    "wxid": "wxid_abc",
    "path": "/path/to/WeChat Files/wxid_abc",
    "msg": "/path/to/.../Msg",
    "filestorage": "/path/to/.../FileStorage",
    "config": "/path/to/.../config",
})
ext.save_manifest()

# 3) Generate a report (with full Chain of Custody template)
ReportGenerator.generate(
    "./out", operations=[], case_id="CASE-001", evidence_id="E001",
)

# 4) Sign the report
sign_report("./out/_forensic_report.json")
```

---

## Output Format

```
wechat_forensic_output/
├── mirrors/                        # Bit-for-bit disk images (forensic mode)
│   └── disk_mirror_20260801_xxxxxx.img
├── PC_wxid_xxxxx/                  # PC WeChat extraction
│   ├── Msg/                        # *.db, *.db-wal, *.db-shm
│   ├── FileStorage/                # images / files / videos
│   └── config/                     # config files
├── Mobile_ios_<UDID>_<8hex>/       # iOS backup
├── Mobile_android_<path8>/         # Android backup
├── _forensic_manifest.json         # overall manifest
├── _forensic_report.json           # forensic report (machine-readable)
├── _forensic_report.txt            # forensic report (human-readable)
├── _signature.json                 # digital signature (with --sign)
├── forensic_log.txt                # operation log
└── wechat_forensic_output_*.zip    # zipped package (with SHA-256)
```

### JSON Report Schema (v2.0.3)

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
    "principle": "Original evidence is immutable; all operations performed on copies/images",
    "hash_algorithm": "SHA-256 (4MB chunk)"
  },
  "chain_of_custody": {
    "case_id": "Forensic-Commission[2026]No.001",
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
    { "step": "Disk image generation", "sha256": "...", "source": "/dev/disk0", ... },
    { "step": "Data extraction", "source": "...", "file_hashes": {...} }
  ]
}
```

### Digital Signature Format (`_signature.json`)

```jsonc
{
  "report_path": "/abs/path/_forensic_report.json",
  "report_sha256": "abc123...",
  "signed_at": "2026-08-01T07:40:24Z",
  "signature_algorithm": "HMAC-SHA256",   // or RSA-PSS-SHA256
  "signature_b64": "...",
  "compliance": {
    "iso_27037": "...",
    "rfc_3227": "..."
  }
}
```

The HMAC key is read from the `WECHAT_FORENSIC_HMAC_KEY` environment variable — **set it in production**.

---

## Cloud Upload (v2.0.5 pluggable)

The cloud-upload step is **fully extensible** since v2.0.5. Beyond the two legacy providers (Baidu, Aliyun), the tool ships with **6 built-in adapters** and an open plugin mechanism for any custom cloud.

### Built-in adapters

| `--upload` | Protocol / SDK | Required extra | Typical providers |
|---|---|---|---|
| `baidu` | `bypy` CLI | `[baidu]` | 百度网盘 |
| `aliyun` | `oss2` | `[aliyun]` | 阿里云 OSS |
| **`s3`** | `boto3` (S3 API) | `[s3]` | AWS S3 · 腾讯 COS · 七牛 Kodo(S3) · 阿里 OSS-S3 · MinIO · 自建 Ceph · Cloudflare R2 |
| **`webdav`** | `webdavclient3` | `[webdav]` | 坚果云 · Nextcloud · ownCloud · OneDrive (WebDAV mode) |
| **`sftp`** | `paramiko` | `[sftp]` | 自建 SFTP · 树莓派 NAS · 老旧服务器 |
| **`local`** | stdlib only | (none) | NAS 挂载点 · USB 移动硬盘 · 第二块硬盘 |
| `none` | (skip upload) | — | default |

> **Tip**: 90% of "self-defined cloud" scenarios can be covered by `s3` alone — just change `endpoint_url`. Most providers (Tencent COS, Qiniu, Aliyun OSS-S3 mode, MinIO, Cloudflare R2) are S3-compatible.

### Quick start: any S3-compatible cloud

```yaml
# ~/.config/wechat-forensic/upload.yaml
s3:
  endpoint_url: https://cos.ap-guangzhou.myqcloud.com   # 腾讯 COS
  region: ap-guangzhou
  bucket: example-1250000000
  access_key: AKIDxxxxxxxxxxxxxxxxxxxx
  secret_key: xxxxxxxxxxxxxxxxxxxxxxxx
  prefix: wechat_forensic/
```

```bash
wechat-forensic --upload s3 --upload-config ~/.config/wechat-forensic/upload.yaml
```

### Configuration priority (high → low)
1. CLI flag `--upload-config <path>`
2. Environment `$WECHAT_FORENSIC_UPLOAD_CONFIG` (file path)
3. `~/.config/wechat-forensic/upload.yaml` (default location)
4. Inline env vars: `WECHAT_FORENSIC_UPLOAD_<NAME>_<FIELD>=value`
   (e.g. `WECHAT_FORENSIC_UPLOAD_S3_BUCKET=my-bucket`)

### List all available uploaders
```bash
wechat-forensic --upload-list
```

### Plugin mechanism (any custom cloud)
Drop a Python file into one of these two directories and it will be discovered automatically:
- `~/.config/wechat-forensic/plugins/uploaders/` (user-level, cross-project)
- `<project>/uploaders/` (project-level)

Minimal template:
```python
from wechat_forensic.uploader import UploaderBase

class MyCloudUploader(UploaderBase):
    name = "my-cloud"
    display_name = "My Company Cloud"
    required_deps = ["my-sdk"]

    def upload(self, file, logger=None, config=None):
        # your upload logic here
        return self._return_success("remote://path", {"extra": "info"})
```

See [`examples/uploaders/`](examples/uploaders/) for **Tencent COS** and **Qiniu Kodo** complete examples and [`examples/uploaders/README.md`](examples/uploaders/README.md) for the full guide.

---

## WeChat Data Path Table

| Platform             | Full Path                                                                          | Privilege Required                  | Notes                                |
|----------------------|------------------------------------------------------------------------------------|-------------------------------------|--------------------------------------|
| **Windows PC**       | `%USERPROFILE%\Documents\WeChat Files\`                                            | User                                | Custom install may change the path   |
| **macOS PC**         | `~/Library/Containers/com.tencent.xinWeChat/Data/Library/Application Support/com.tencent.xinWeChat/` | User                                | Full App Sandbox path                |
| **Linux PC**         | `~/.config/wechat`                                                                 | User                                | CrossOver/Wine layout                |
| **iOS Backup**       | `~/Library/Application Support/MobileSync/Backup/<UDID>/`                          | User                                | Folder name = UDID (lowercase hex, no dashes) |
| **Android 11+**      | `/sdcard/Android/data/com.tencent.mm/MicroMsg/`                                    | **Root or Shizuku**                 | Scoped Storage restriction           |
| **Android 10-**      | `/sdcard/tencent/MicroMsg/`                                                        | User                                | `adb pull` works                     |
| **Android DB**       | `/data/data/com.tencent.mm/MicroMsg/<32-hex-MD5>/EnMicroMsg.db`                    | **Root**                            | SQLCipher-encrypted                  |

### WeChat Database Encryption (EnMicroMsg.db)
- **Algorithm**: SQLCipher (AES-256-CBC)
- **Key derivation**: `MD5(IMEI + UIN)[0:7]` (first 7 chars of MD5)
- **This tool**: only performs bit-for-bit extraction; **decryption is NOT included**
- **Decryption references**: [wechat-dbcracker](https://github.com/Hill1976/WechatExporter), wxsqlcipher
- **Legal note**: decrypting someone else's WeChat data still requires lawful authorization

---

## Compliance Framework

This tool's forensic flow references:

- **ISO/IEC 27037:2012** — Guidelines for identification, collection, acquisition and preservation of digital evidence
- **ISO/IEC 27042:2015** — Guidelines for the analysis and interpretation of digital evidence
- **RFC 3227** — IETF best practices for evidence collection (Use copies, avoid contamination, record everything)
- **NIST SP 800-86** — Guide to integrating forensic techniques into incident response
- **PRC Supreme People's Court Provisions on Civil Litigation Evidence** — electronic-data clauses

See `wechat_forensic/security.py` and `wechat_forensic/report.py` for field definitions.

---

## Limitations & Disclaimer

### Tool Limitations
1. **No EnMicroMsg.db decryption** — independent tools required after extraction
2. **No verification of original device authenticity** — only the extracted copy is hashed
3. **Bit-for-bit imaging requires root/admin** — privilege requirements differ per platform
4. **Android 11+ Scoped Storage** — requires root or Shizuku
5. **macOS sandbox path** — launch WeChat once before extraction
6. **Encrypted iOS backup** — iTunes backup password required (not handled directly by this version)

### Judicial Limitations
1. This report is an **operation log**, **not a judicial forensic opinion**
2. Judicial opinions must be issued by a **CNAS/CMA-accredited** forensic institute
3. The report's judicial weight depends on: write-blocking hardware, witness presence, complete chain of custody, and signature legality

### Ethical Limitations
1. **Never** use this tool on unauthorized devices
2. Users must independently assess the law of their jurisdiction
3. The authors **bear no liability** for misuse

---

## Development & Testing

```bash
git clone https://github.com/serenashenn3-art/wechat-forensic-pro.git
cd wechat-forensic-pro
pip install -e ".[dev,all]"

# Run tests (29 cases, covers key bug fixes)
pytest tests/ -v --cov=wechat_forensic

# One-shot check (lint + test + CLI smoke)
bash scripts/verify.sh
```

See [CONTRIBUTING.md](CONTRIBUTING.md). **Never** commit real WeChat data, images, zips, or reports.

---

## AI Agent Skills

This repository ships dedicated **Skill** manifests so AI tools can load the project directly:

| Tool           | Skill file                                  |
|----------------|---------------------------------------------|
| **Kimi Work**  | [skills/kimi-work/SKILL.md](skills/kimi-work/SKILL.md) |
| **Codex**      | [skills/codex/SKILL.md](skills/codex/SKILL.md)         |
| **Claude**     | [skills/claude/SKILL.md](skills/claude/SKILL.md)       |
| **Hermes**     | [skills/hermes/SKILL.md](skills/hermes/SKILL.md)       |
| **OpenClaw**   | [skills/openclaw/SKILL.md](skills/openclaw/SKILL.md)   |
| **TRAE**       | [AGENTS.md](AGENTS.md)                                   |

---

## License & Ethics

### Code License: MIT

```
MIT License

Copyright (c) 2026 WeChat Forensic Pro Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction ...
```

Full terms in [LICENSE](LICENSE).

### ⚠️ Relationship between MIT and end-use

> **Legal disclaimer**: this section is provided by the project maintainers, for reference only, and is not legal advice.

The MIT license itself **only governs the code-level grant** (use, copy, modify, distribute) — it **cannot** unilaterally restrict the end-use of the code via the LICENSE file. This is true of all open-source licenses.

The project therefore uses a **dual constraint** mechanism:

1. **Code grant** = MIT license (you may freely use, modify, distribute the code)
2. **End-use constraint** = [AGENTS.md](AGENTS.md) + this README's legal notice + applicable laws

Violating the end-use constraint **does not** automatically revoke your code grant (since MIT has no such clause), BUT:

- Violating local law exposes **you** to personal liability (the project bears none)
- AI tools that read `AGENTS.md` will **actively refuse** to assist with violations
- Maintainers reserve the right to **withdraw infringing distributions** from PyPI / GitHub Releases (under DMCA or equivalent)

### Jurisdiction Notes
- **PRC**: Criminal Law Art. 285, Data Security Law, Personal Information Protection Law
- **EU**: GDPR Article 6
- **US**: CFAA + state laws (e.g. CCPA)

---

## Feedback

- Bug Report: [GitHub Issues](https://github.com/serenashenn3-art/wechat-forensic-pro/issues/new/choose)
- Feature requests for legitimate authorized scenarios are welcome
- "Feature requests" for unauthorized scenarios will be closed immediately

---

## Related Projects

- [wechat-dbcracker](https://github.com/Hill1976/WechatExporter) — EnMicroMsg.db decryption reference
- [WxSqlcipher](https://github.com/ppwwyyxx/wechat-dump) — WeChat database export
- [Autopsy](https://www.autopsy.com/) — commercial forensic platform (Windows)
- [Sleuth Kit](https://www.sleuthkit.org/) — open-source forensic framework

---

**Last updated**: 2026-08-02 · v2.0.3 · Made for **legal forensics** by authorized practitioners only.

# 操作时间线 — SAMPLE

> **案件**: SAMPLE-CASE-2026-001
> **证据**: SAMPLE-EVD-001
> **时间跨度**: 2026-08-02 06:00 — 14:00 UTC
> **所有时间为合成数据,仅供 schema 演示**

## 时间线

| 时间 (UTC) | 步骤 | 操作员 | 工具/方法 | 关键产物 | SHA-256 (前 12 字符) |
|---|---|---|---|---|---|
| 06:00:00 | 接入写保护桥 | demo-user | SAMPLE-T8u | — | — |
| 06:00:30 | 启动工具 + 设备扫描 | demo-user | wechat-forensic | `_forensic_report.json` 草稿 | (生成中) |
| 06:01:00 | 磁盘镜像生成 | demo-user | dd (write-blocked) | `disk_mirror_*.img` | `a1b2c3d4e5f6` |
| 06:03:25 | 镜像完成 (145s) | demo-user | dd → sha256sum | `disk_mirror_*.img` | `a1b2c3d4e5f6` |
| 06:05:00 | 定位微信数据 | demo-user | locator.py | 路径: `wxid_sample_0001` | — |
| 06:05:30 | 数据提取 | demo-user | extractor.py | `PC_wxid_sample_0001/` (142 文件) | 各文件独立哈希 |
| 06:08:00 | 清单生成 | demo-user | hashing.py | `_forensic_manifest.json` | manifest-level |
| 06:08:30 | 报告生成 | demo-user | report.py | `_forensic_report.json` | report-level |
| 06:09:00 | 数字签名 (HMAC) | demo-user | security.py | `_signature.json` | key-fp `9f86d081` |
| 07:00:00 | **流转 1**: 移入档案柜 | demo-user → storage-A | 加密外置硬盘 | `evidence_*.zip` | `a1b2c3d4e5f6` |
| 13:00:00 | **流转 2**: 内部交接 | storage-A → demo-lab | 见证人 demo-witness | 内部签收单 | — |
| 13:30:00 | 复核 + 完整性校验 | demo-witness | sha256sum 重新计算 | 校验报告 | (匹配 ✓) |
| 14:00:00 | 报告定稿 | demo-user | report.py → 封存 | `_forensic_report.json` final | report-level |
| 14:00:30 | 签名附加 (定稿) | demo-user | security.py | `_signature.json` final | key-fp `9f86d081` |

## 关键控制点

### ✓ 写保护确认
- **时间**: 06:00:00
- **设备**: SAMPLE-T8u (序列号 SN-SAMPLE-001)
- **状态**: 启用
- **意义**: 司法采信的核心 — 证明源盘在镜像过程中**未被修改**

### ✓ 哈希链完整
- 磁盘镜像 SHA-256 → 提取操作源 → manifest 哈希 → 报告哈希 → 签名
- 任何一环被篡改,后续环节的哈希都会**失配**

### ✓ 见证人在场
- 06:00 — 14:00 全程: demo-witness
- 13:30 复核时: demo-witness 重新计算 SHA-256 并比对

### ✓ 密钥分离
- 签名密钥: 不在证据包中存储明文
- 密钥指纹 (SHA-256): `9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08`
- 实际密钥: 应通过独立渠道(加密邮件 / 硬件 token)交付,不与证据 zip 同渠道

## 警告

本样例时间线**完全虚构**,所有操作员、见证人、设备、时间点、哈希值
都是 mock 数据,不可用于任何真实案件的合规审计。

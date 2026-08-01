"""取证安全与合规框架

参考标准:
  - ISO/IEC 27037:2012 - 识别、收集、获取和保存数字证据的指南
  - ISO/IEC 27042:2015 - 数字证据分析与解释指南
  - RFC 3227 - 收集和归档证据的最佳实践 (IETF)
  - NIST SP 800-86 - 集成取证过程指南
  - 中国《电子数据司法解释》- 最高人民法院关于民事诉讼证据的若干规定

核心原则 (RFC 3227):
  1. 原始证据不可修改 (Use copies)
  2. 谨慎处理证据以避免污染 (Avoid contamination)
  3. 记录所有操作 (Record everything)
  4. 完整保存证据 (Be prepared to testify)
"""

import base64
import hashlib
import hmac
import json
import os
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sign_report(report_path: str, private_key_pem: Optional[bytes] = None) -> dict:
    """对取证报告做数字签名,防止事后篡改

    两种模式:
      1. 私钥模式 (司法鉴定场景): RSA-PSS 签名
      2. HMAC 模式 (内部审计): 共享密钥签名

    验证方式:
      - RSA: 公钥可发布,任何持有公钥的人能验证
      - HMAC: 双方持有相同密钥

    Returns: 签名信息 dict (写入报告同目录的 _signature.json)
    """
    report_sha256 = sha256_file(report_path)
    sig_info = {
        "report_path": str(Path(report_path).resolve()),
        "report_sha256": report_sha256,
        "signed_at": datetime.now(timezone.utc).isoformat(),
        "signer": {
            "hostname": socket.gethostname(),
            "user": os.environ.get("USER") or os.environ.get("USERNAME"),
        },
        "compliance": {
            "iso_27037": "原始证据不可修改;所有操作记录在案",
            "rfc_3227": "Use copies, avoid contamination, record everything",
            "nist_sp_800_86": "使用 SHA-256 校验完整性",
        },
    }

    if private_key_pem:
        # RSA 私钥签名 (需要 cryptography 库)
        try:
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding

            private_key = serialization.load_pem_private_key(private_key_pem, password=None)
            signature = private_key.sign(
                report_sha256.encode("utf-8"),
                padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
                hashes.SHA256(),
            )
            sig_info["signature_algorithm"] = "RSA-PSS-SHA256"
            sig_info["signature_b64"] = base64.b64encode(signature).decode("ascii")
            sig_info["public_key_fingerprint"] = hashlib.sha256(
                private_key.public_key().public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo,
                )
            ).hexdigest()
        except ImportError:
            sig_info["error"] = "cryptography 库未安装,回退到 HMAC 模式"
            sig_info["signature_b64"] = _hmac_sign(report_sha256)
            sig_info["signature_algorithm"] = "HMAC-SHA256"
    else:
        sig_info["signature_b64"] = _hmac_sign(report_sha256)
        sig_info["signature_algorithm"] = "HMAC-SHA256"

    sig_path = Path(report_path).parent / "_signature.json"
    with open(sig_path, "w", encoding="utf-8") as f:
        json.dump(sig_info, f, ensure_ascii=False, indent=2)
    return sig_info


def _hmac_sign(message: str) -> str:
    """HMAC-SHA256 签名,密钥从环境变量 WECHAT_FORENSIC_HMAC_KEY 读取"""
    key = os.environ.get(
        "WECHAT_FORENSIC_HMAC_KEY",
        "default-insecure-key-set-WECHAT_FORENSIC_HMAC_KEY-env-var",
    ).encode("utf-8")
    sig = hmac.new(key, message.encode("utf-8"), hashlib.sha256).digest()
    return base64.b64encode(sig).decode("ascii")


def chain_of_custody_template() -> dict:
    """Chain of Custody 模板 — 在 ISO/IEC 27037 框架下记录

    Required fields per ISO/IEC 27037:
      - case_id / evidence_id
      - acquisition_date / acquisition_location
      - acquired_by (operator)
      - acquisition_method (镜像/提取方式)
      - integrity_hash (SHA-256)
      - storage_location
      - transfer_chain (每个转手记录)
    """
    return {
        "compliance_framework": [
            "ISO/IEC 27037:2012",
            "ISO/IEC 27042:2015",
            "RFC 3227",
            "NIST SP 800-86",
        ],
        "case_id": "<案件编号 / 委托函编号>",
        "evidence_id": "<证据编号 (E001, E002, ...)>",
        "acquisition": {
            "date_utc": datetime.now(timezone.utc).isoformat(),
            "location": "<取证现场 / 实验室地址>",
            "operator": "<操作员姓名 + 资质证书号>",
            "witness": "<见证人姓名 + 资质 (建议至少 1 名)>",
            "method": "<dd | python_raw_copy | forensic_directory_mirror>",
            "source": {
                "device_type": "<PC | iOS | Android | 物理磁盘>",
                "make_model": "<设备品牌型号>",
                "serial": "<设备序列号 / IMEI / UDID>",
                "os": "<操作系统版本>",
            },
            "write_blocking": {
                "used": True,
                "tool": "<硬件写保护桥型号, 如 Tableau / WiebeTech>",
                "or_software": "<如仅软件方式, 记录 fs_mounted_ro 等>",
            },
        },
        "integrity": {
            "hash_algorithm": "SHA-256",
            "hash": "<镜像/提取物的 SHA-256>",
            "verified_by": "<验证人 + 时间>",
        },
        "transfer_chain": [
            {
                "from": "<前一手>",
                "to": "<后一手>",
                "date_utc": "<转交时间>",
                "method": "<当面交付 / 加密传输>",
                "witness": "<见证人>",
                "hash_before": "<转交前哈希>",
                "hash_after": "<转交后哈希 (验证未篡改)>",
            }
        ],
        "storage": {
            "current_location": "<当前物理位置 / 加密存储位置>",
            "encryption": "<AES-256 / VeraCrypt / 硬件加密>",
            "access_control": "<双人规则 / 单人 + 监控>",
        },
        "disposal": {
            "method": "<到期后如何销毁>",
            "scheduled_date": "<销毁日期>",
        },
    }


def recommend_write_blocking() -> str:
    """输出写保护建议 (ISO 27037 §6.4 强制要求)"""
    return """
# 写保护建议 (ISO/IEC 27037 §6.4)

## 强烈推荐: 硬件写保护桥
- Tableau Forensic SATA/IDE Bridge (T8u, T9)
- WiebeTech WriteBlocker
- CRU WiebeTech ComboDock

## 软件级降级方案 (需在可信环境使用)
- Linux: `mount -o ro,noload /dev/sdX /mnt/evidence`
- macOS: `mount -t hfs -o rdonly /dev/diskX /mnt/evidence`
- Windows: `fsutil volume dismount <volume>` + FTK Imager 做只读镜像

## 取证流程检查清单
- [ ] 设备到达时拍照记录 (外观、屏幕、序列号)
- [ ] 整个取证过程中设备不可联网
- [ ] 写保护桥接入后再开机
- [ ] 原始磁盘绝不再挂载为可写
- [ ] 所有操作记录在 Chain of Custody 文档
- [ ] 取证完成后设备封存并贴封条
"""

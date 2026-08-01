"""security.py + report.py v2.0.3 新增字段测试"""

import json
import os
import tempfile
from pathlib import Path


def test_chain_of_custody_has_iso_27037_fields(stub_logger):
    from wechat_forensic.security import chain_of_custody_template

    coc = chain_of_custody_template()
    assert "compliance_framework" in coc
    assert "ISO/IEC 27037" in coc["compliance_framework"][0]
    assert "case_id" in coc
    assert "evidence_id" in coc
    assert "acquisition" in coc
    assert "write_blocking" in coc["acquisition"]
    assert "transfer_chain" in coc
    assert "storage" in coc


def test_sign_report_produces_hmac_signature(stub_logger, tmp_path, monkeypatch):
    """设置 HMAC key 后, 签名应稳定生成"""
    from wechat_forensic.security import sign_report

    monkeypatch.setenv("WECHAT_FORENSIC_HMAC_KEY", "test-key-12345")

    report = tmp_path / "_forensic_report.json"
    report.write_text('{"hello": "world"}', encoding="utf-8")

    sig = sign_report(str(report))
    assert sig["signature_algorithm"] == "HMAC-SHA256"
    assert "signature_b64" in sig
    assert "report_sha256" in sig
    assert sig["report_sha256"]  # 非空

    # 签名文件落在同目录
    sig_path = tmp_path / "_signature.json"
    assert sig_path.exists()
    sig_data = json.loads(sig_path.read_text(encoding="utf-8"))
    assert sig_data["report_sha256"] == sig["report_sha256"]


def test_sign_report_without_key_rejected(stub_logger, tmp_path, monkeypatch):
    """不设置 WECHAT_FORENSIC_HMAC_KEY 时, 应拒绝签名而不是使用不安全默认值"""
    from wechat_forensic.security import sign_report

    monkeypatch.delenv("WECHAT_FORENSIC_HMAC_KEY", raising=False)
    report = tmp_path / "_forensic_report.json"
    report.write_text("{}", encoding="utf-8")
    sig = sign_report(str(report))
    assert sig["signature_algorithm"] == "HMAC-SHA256"
    assert "error" in sig
    assert "WECHAT_FORENSIC_HMAC_KEY" in sig["error"]


def test_report_generator_with_case_id(stub_logger, tmp_path):
    """CLI --case-id / --evidence-id 应能传入 ReportGenerator"""
    from wechat_forensic.report import ReportGenerator

    txt = ReportGenerator.generate(
        str(tmp_path),
        [{"step": "测试", "timestamp": "t", "description": "d"}],
        logger=stub_logger,
        case_id="CASE-2026-001",
        evidence_id="E001",
    )
    body = open(txt, encoding="utf-8").read()
    assert "CASE-2026-001" in body
    assert "E001" in body
    assert "ISO/IEC 27037" in body
    assert "证据链" in body
    assert "局限性与免责声明" in body

    # JSON 也要有完整 chain_of_custody
    json_path = tmp_path / "_forensic_report.json"
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["chain_of_custody"]["case_id"] == "CASE-2026-001"
    assert data["chain_of_custody"]["evidence_id"] == "E001"
    assert "ISO/IEC 27037" in data["compliance"]["frameworks"][0]

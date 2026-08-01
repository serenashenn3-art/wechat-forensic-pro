"""取证报告测试 (覆盖 v2.0.1 关键 bug 修复: \n 不能写成 \\n)"""

import pytest

from wechat_forensic.report import ReportGenerator, ReportValidationError


def test_text_report_has_real_newlines(stub_logger, tmp_path):
    out = ReportGenerator.generate(
        str(tmp_path),
        [{"step": "测试", "timestamp": "t", "description": "d",
          "sha256": "abc", "source": "s", "output": "o"}],
        logger=stub_logger,
        case_id="CASE-TEST-001",
        evidence_id="E-TEST-001",
    )
    body = open(out, encoding="utf-8").read()
    # 关键: 不能有字面 \\n
    assert "\\n" not in body, "报告中所有换行必须是真实换行, 不能是字面 \\n"
    # 必须有真实换行
    assert "\n" in body
    # 关键中文标题不能丢
    assert "微信聊天记录取证报告" in body
    # v2.0.3 新增章节
    assert "证据链 (Chain of Custody)" in body
    assert "合规框架 (Compliance Framework)" in body
    assert "局限性与免责声明" in body
    # 完整性声明
    assert "完整性声明" in body


def test_json_report_structure(stub_logger, tmp_path):
    import json
    from wechat_forensic import __version__

    ReportGenerator.generate(
        str(tmp_path),
        [{"step": "测试"}],
        logger=stub_logger,
        case_id="CASE-TEST-001",
        evidence_id="E-TEST-001",
    )
    json_path = tmp_path / "_forensic_report.json"
    data = json.loads(json_path.read_text(encoding="utf-8"))
    # schema: tool 是 dict, version 与当前包版本一致
    assert data["tool"]["name"].startswith("WeChat Forensic Extractor Pro")
    assert data["tool"]["version"] == __version__
    assert "operations" in data
    assert "chain_of_custody" in data
    assert "compliance" in data
    # ISO 27037 字段
    assert data["chain_of_custody"]["compliance_framework"][0] == "ISO/IEC 27037:2012"
    assert data["compliance"]["hash_algorithm"].startswith("SHA-256")


def test_report_with_case_id(stub_logger, tmp_path):
    """v2.0.3 新参数: case_id / evidence_id 注入 Chain of Custody"""
    import json
    ReportGenerator.generate(
        str(tmp_path),
        [{"step": "测试"}],
        logger=stub_logger,
        case_id="司法鉴定委托函[2026]第001号",
        evidence_id="E001",
    )
    data = json.loads((tmp_path / "_forensic_report.json").read_text(encoding="utf-8"))
    assert data["chain_of_custody"]["case_id"] == "司法鉴定委托函[2026]第001号"
    assert data["chain_of_custody"]["evidence_id"] == "E001"


def test_report_requires_case_and_evidence_id(stub_logger, tmp_path):
    """Chain of Custody 核心字段缺失时应拒绝生成报告。"""
    with pytest.raises(ReportValidationError):
        ReportGenerator.generate(
            str(tmp_path),
            [{"step": "测试"}],
            logger=stub_logger,
        )

    with pytest.raises(ReportValidationError):
        ReportGenerator.generate(
            str(tmp_path),
            [{"step": "测试"}],
            logger=stub_logger,
            case_id="<案件编号 / 委托函编号>",
            evidence_id="E001",
        )

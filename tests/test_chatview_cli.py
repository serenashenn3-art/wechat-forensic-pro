"""cli.py chatview 模式授权选择测试

测试 _resolve_authorization 的 A/B 分类与留痕逻辑,
不涉及真实微信数据或解密代码。
"""

import argparse

import pytest

from wechat_forensic.cli import _resolve_authorization


def _args(authorization=None, no_interactive=False):
    return argparse.Namespace(
        authorization=authorization,
        no_interactive=no_interactive,
    )


def test_authorization_explicit_a():
    """显式 --authorization 以 A 开头 -> 类型 A"""
    at, text = _resolve_authorization(_args(authorization="A-个人设备/wxid_self"))
    assert at == "A"
    assert text == "A-个人设备/wxid_self"


def test_authorization_explicit_b():
    """显式 --authorization 以 B 开头 -> 类型 B"""
    at, text = _resolve_authorization(_args(authorization="B-司法鉴定委托函[2026]第001号"))
    assert at == "B"
    assert text == "B-司法鉴定委托函[2026]第001号"


def test_authorization_no_prefix_defaults_b():
    """显式 --authorization 无 A/B 前缀 -> 默认 B(需明确依据的场景)"""
    at, text = _resolve_authorization(_args(authorization="企业合规审计-员工书面同意-工号A001"))
    assert at == "B"
    assert text == "企业合规审计-员工书面同意-工号A001"


def test_authorization_missing_non_interactive_fails():
    """非交互模式且无 --authorization -> 返回空, _run_chatview 会报错退出"""
    at, text = _resolve_authorization(_args(no_interactive=True))
    assert at == ""
    assert text == ""


@pytest.mark.parametrize("choice,detail,expected_type,expected_prefix", [
    ("A", "wxid_self", "A", "A-个人取证-本人设备/wxid_self"),
    ("A", "", "A", "A-个人取证-本人设备"),
    ("B", "企业合规审计-员工书面同意-工号A001", "B", "B-企业合规审计-员工书面同意-工号A001"),
])
def test_authorization_interactive(monkeypatch, choice, detail, expected_type, expected_prefix):
    """交互模式下 A/B 选择生成正确授权字符串"""
    inputs = iter([choice, detail])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(inputs))
    at, text = _resolve_authorization(_args())
    assert at == expected_type
    assert text == expected_prefix


def test_authorization_interactive_b_empty_detail_fails(monkeypatch):
    """交互模式下 B 类不填具体依据 -> 返回空"""
    inputs = iter(["B", ""])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(inputs))
    at, text = _resolve_authorization(_args())
    assert at == ""
    assert text == ""


def test_authorization_interactive_invalid_choice_fails(monkeypatch):
    """交互模式下选择非 A/B -> 返回空"""
    monkeypatch.setattr("builtins.input", lambda _prompt="": "C")
    at, text = _resolve_authorization(_args())
    assert at == ""
    assert text == ""

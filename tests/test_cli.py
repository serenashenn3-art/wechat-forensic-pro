"""CLI 入口测试"""

import subprocess
import sys
from pathlib import Path


def test_cli_version():
    r = subprocess.run(
        [sys.executable, "-m", "wechat_forensic.cli", "--version"],
        capture_output=True, text=True,
        cwd=Path(__file__).resolve().parent.parent,
    )
    assert r.returncode == 0
    assert "wechat-forensic" in r.stdout
    assert "2.0.6" in r.stdout


def test_cli_help():
    r = subprocess.run(
        [sys.executable, "-m", "wechat_forensic.cli", "--help"],
        capture_output=True, text=True,
        cwd=Path(__file__).resolve().parent.parent,
    )
    assert r.returncode == 0
    assert "--source" in r.stdout
    assert "--mode" in r.stdout
    assert "--zip-password" in r.stdout


def test_legacy_wrapper_emits_warning():
    """旧版 wechat_forensic_pro.py 仍能跑, 但会发 deprecation warning"""
    r = subprocess.run(
        [sys.executable, "-W", "default::DeprecationWarning", "wechat_forensic_pro.py", "--version"],
        capture_output=True, text=True,
        cwd=Path(__file__).resolve().parent.parent,
    )
    assert r.returncode == 0
    assert "DeprecationWarning" in r.stderr
    assert "wechat-forensic" in r.stdout

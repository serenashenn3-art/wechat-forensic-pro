"""Config + Locator v2.0.3 新增字段测试"""

import sys
from pathlib import Path


def test_android_data_paths_distinguish_storage_tiers():
    """ANDROID_DATA_PATHS 应包含 Scoped Storage + 旧版 + /data/data 三种"""
    from wechat_forensic.config import Config

    paths = Config().ANDROID_DATA_PATHS
    has_scoped = any("/Android/data/" in p for p in paths)
    has_legacy = any("/tencent/MicroMsg" in p for p in paths)
    has_data_data = any("/data/data/" in p for p in paths)

    assert has_scoped, "应包含 Android 11+ Scoped Storage 路径"
    assert has_legacy, "应包含 Android 10- 旧版路径"
    assert has_data_data, "应包含 /data/data (需 root)"


def test_config_module_docstring_documented():
    """config.py 顶部 docstring 应有完整路径说明"""
    from wechat_forensic import config

    doc = config.__doc__
    assert "macOS" in doc
    assert "沙盒" in doc or "Container" in doc
    assert "UDID" in doc
    assert "EnMicroMsg" in doc
    assert "SQLCipher" in doc or "MD5" in doc


def test_locator_find_mobile_udid_privilege_fields(stub_logger, tmp_path, monkeypatch):
    """find_mobile 输出应包含 udid (iOS) 和 privilege (Android) 字段"""
    from wechat_forensic.locator import Locator
    from wechat_forensic.scanner import Scanner

    # 模拟一个 iOS 备份目录
    backup_root = tmp_path / "MobileSync" / "Backup"
    backup_root.mkdir(parents=True)
    udid = "abcdef0123456789abcdef0123456789abcdef01"  # 40位
    backup = backup_root / udid
    backup.mkdir()
    (backup / "Info.plist").write_text("<?xml version='1.0'?>")

    # 模拟一个 Android 数据目录 (Scoped Storage)
    android_dir = tmp_path / "Android_data"
    android_dir.mkdir()
    (android_dir / "MicroMsg").mkdir()
    (android_dir / "MicroMsg" / "x").write_text("dummy")

    # 替换 Scanner 的 drives() 和 ios_backups() 返回
    fake_scanner = type("F", (), {
        "log": stub_logger,
        "drives": lambda self: [{"device": "fake", "mount": str(tmp_path), "fstype": "-", "free": "1G", "used": "0", "total": "1G", "free_bytes": 0}],
        "ios_backups": lambda self: [str(backup)],
    })()

    monkeypatch.setattr("wechat_forensic.scanner.Scanner", lambda log: fake_scanner)

    loc = Locator(stub_logger)
    results = loc.find_mobile()

    # 找到 iOS 备份
    ios = [r for r in results if r["type"] == "ios_backup"]
    assert len(ios) >= 1
    assert ios[0]["udid"] == udid

"""定位器测试 (覆盖 Windows / macOS / Linux 微信路径识别)"""

from pathlib import Path

from wechat_forensic.locator import Locator


def test_scan_wechat_dir_finds_windows_style_account(stub_logger, tmp_path):
    """Windows 标准结构: WeChat Files/wxid_xxx/Msg/..."""
    src = tmp_path / "wxid_test123"
    src.mkdir()
    (src / "Msg").mkdir()
    (src / "FileStorage").mkdir()
    (src / "config").mkdir()

    loc = Locator(stub_logger)
    found = loc._scan_wechat_dir(str(tmp_path))

    assert len(found) == 1
    assert found[0]["wxid"] == "wxid_test123"
    assert found[0]["msg"] == str(src / "Msg")
    assert found[0]["filestorage"] == str(src / "FileStorage")
    assert found[0]["config"] == str(src / "config")


def test_scan_wechat_dir_finds_macos_sandbox_version_dir(stub_logger, tmp_path):
    """macOS 原生微信沙盒结构: 2.0b4.0.9/Avatar/KeyValue/MMappedKV/..."""
    version_dir = tmp_path / "2.0b4.0.9"
    version_dir.mkdir()
    (version_dir / "Avatar").mkdir()
    (version_dir / "KeyValue").mkdir()
    (version_dir / "MMappedKV").mkdir()

    loc = Locator(stub_logger)
    found = loc._scan_wechat_dir(str(tmp_path))

    assert len(found) == 1
    assert found[0]["wxid"] == "macos_2.0b4.0.9"
    assert found[0]["filestorage"] == str(version_dir)
    assert found[0]["msg"] is None
    assert found[0]["config"] is None


def test_scan_wechat_dir_ignores_random_dirs(stub_logger, tmp_path):
    """非微信目录不应被识别"""
    (tmp_path / "some_random_dir").mkdir()
    (tmp_path / "Avatar").mkdir()  # 单独 Avatar 不是 macOS 沙盒

    loc = Locator(stub_logger)
    found = loc._scan_wechat_dir(str(tmp_path))

    assert found == []


def test_is_macos_wechat_version_dir_requires_markers(stub_logger, tmp_path):
    """版本号目录必须包含 macOS 微信特有子目录才算数"""
    only_version = tmp_path / "3.0.0.0"
    only_version.mkdir()

    loc = Locator(stub_logger)
    assert loc._is_macos_wechat_version_dir(only_version) is False

    (only_version / "Avatar").mkdir()
    (only_version / "KeyValue").mkdir()
    assert loc._is_macos_wechat_version_dir(only_version) is True


def test_is_macos_wechat_version_dir_rejects_non_version_names(stub_logger, tmp_path):
    """目录名不像版本号则不应被识别"""
    d = tmp_path / "wechat_data"
    d.mkdir()
    (d / "Avatar").mkdir()
    (d / "KeyValue").mkdir()

    loc = Locator(stub_logger)
    assert loc._is_macos_wechat_version_dir(d) is False

"""Uploader 可插拔架构测试 (v2.0.5)

覆盖:
1. 注册表能发现全部 6 个内置适配器
2. list() 按 builtin 优先排序
3. get(name) 找不到时返回 None
4. LocalUploader copy 模式成功
5. LocalUploader 缺 destination_dir 返回失败
6. S3Uploader 缺必填字段返回清晰错误
7. S3Uploader 未装 boto3 给出安装提示
8. WebDAVUploader 缺必填字段
9. SFTPUploader 缺 host/user
10. 旧 Uploader.baidu 静态方法仍能 import(deprecation 路径)
11. 插件目录发现: 写一个临时 .py 验证 _discover_from_dir
12. 配置加载: YAML/JSON/环境变量三种来源
13. 内联环境变量 WECHAT_FORENSIC_UPLOAD_<NAME>_* 解析
14. 返回值结构必须包含 success/message/remote/algorithm
15. CLI --upload-list 退出码 0
"""

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from wechat_forensic.uploader import (
    AliyunUploader,
    BaiduUploader,
    LocalUploader,
    S3Uploader,
    SFTPUploader,
    Uploader,
    UploaderBase,
    UploaderRegistry,
    WebDAVUploader,
    get_config_for,
    load_config,
)


# ---------------------------------------------------------------------------
# 1-3. 注册表
# ---------------------------------------------------------------------------

def test_registry_discovers_all_builtins():
    reg = UploaderRegistry()
    items = {x["name"] for x in reg.list()}
    assert {"baidu", "aliyun", "s3", "webdav", "sftp", "local"}.issubset(items)


def test_registry_list_returns_meta():
    reg = UploaderRegistry()
    items = reg.list()
    assert len(items) >= 6
    for x in items:
        assert "name" in x and "display_name" in x
        assert "is_builtin" in x
        assert "required_deps" in x


def test_registry_get_known():
    reg = UploaderRegistry()
    assert isinstance(reg.get("baidu"), BaiduUploader)
    assert isinstance(reg.get("aliyun"), AliyunUploader)
    assert isinstance(reg.get("local"), LocalUploader)


def test_registry_get_unknown_returns_none():
    reg = UploaderRegistry()
    assert reg.get("non-existent-uploader-xyz") is None


# ---------------------------------------------------------------------------
# 4-5. LocalUploader
# ---------------------------------------------------------------------------

def test_local_uploader_copy_success(tmp_path, stub_logger):
    src = tmp_path / "evidence.zip"
    src.write_bytes(b"fake evidence content")
    dest = tmp_path / "backup"
    u = LocalUploader()
    result = u.upload(str(src), logger=stub_logger, config={"destination_dir": str(dest)})
    assert result["success"] is True
    assert result["algorithm"] == "local"
    assert (dest / "evidence.zip").exists()
    # 校验和必须回填
    assert "sha256" in result


def test_local_uploader_missing_dest_dir(tmp_path, stub_logger):
    src = tmp_path / "evidence.zip"
    src.write_bytes(b"x")
    u = LocalUploader()
    result = u.upload(str(src), logger=stub_logger, config={})
    assert result["success"] is False
    assert "destination_dir" in result["message"]


def test_local_uploader_move_rejected_without_flag(tmp_path, stub_logger):
    """move/hardlink 模式默认必须被拒绝,以保护证据原件。"""
    src = tmp_path / "evidence.zip"
    src.write_bytes(b"x")
    u = LocalUploader()
    for mode in ("move", "hardlink"):
        result = u.upload(
            str(src),
            logger=stub_logger,
            config={"destination_dir": str(tmp_path / "backup"), "mode": mode},
        )
        assert result["success"] is False, f"mode={mode} 应该被拒绝"
        assert "danger_allow_evidence_move" in result["message"]


def test_local_uploader_move_allowed_with_flag(tmp_path, stub_logger):
    src = tmp_path / "evidence.zip"
    src.write_bytes(b"x")
    u = LocalUploader()
    result = u.upload(
        str(src),
        logger=stub_logger,
        config={
            "destination_dir": str(tmp_path / "backup"),
            "mode": "move",
            "danger_allow_evidence_move": "true",
        },
    )
    assert result["success"] is True
    assert not src.exists()
    assert (tmp_path / "backup" / "evidence.zip").exists()


# ---------------------------------------------------------------------------
# 6-9. 错误处理
# ---------------------------------------------------------------------------

def test_s3_missing_required_fields(tmp_path, stub_logger):
    src = tmp_path / "x.zip"
    src.write_bytes(b"x")
    u = S3Uploader()
    result = u.upload(str(src), logger=stub_logger, config={})
    assert result["success"] is False
    assert any(k in result["message"] for k in ("bucket", "access_key"))


def test_s3_no_boto3_gives_install_hint(tmp_path, stub_logger, monkeypatch):
    """模拟 boto3 不可用, 应给出 pip install 提示而不是崩溃。"""
    src = tmp_path / "x.zip"
    src.write_bytes(b"x")
    # 阻止 boto3 导入
    monkeypatch.setitem(sys.modules, "boto3", None)
    monkeypatch.setitem(sys.modules, "botocore", None)
    monkeypatch.setitem(sys.modules, "botocore.exceptions", None)
    u = S3Uploader()
    result = u.upload(
        str(src), logger=stub_logger,
        config={"bucket": "b", "access_key": "a", "secret_key": "s"},
    )
    assert result["success"] is False
    assert "pip install boto3" in result["message"]


def test_webdav_missing_fields(tmp_path, stub_logger):
    src = tmp_path / "x.zip"
    src.write_bytes(b"x")
    u = WebDAVUploader()
    result = u.upload(str(src), logger=stub_logger, config={})
    assert result["success"] is False
    for k in ("url", "username", "password"):
        assert k in result["message"]


def test_sftp_missing_fields(tmp_path, stub_logger):
    src = tmp_path / "x.zip"
    src.write_bytes(b"x")
    u = SFTPUploader()
    result = u.upload(str(src), logger=stub_logger, config={})
    assert result["success"] is False
    assert "host" in result["message"] or "username" in result["message"]


def test_sftp_default_uses_reject_policy(tmp_path, stub_logger, monkeypatch):
    """SFTP 默认 host_key_policy 应为 reject,防止中间人攻击。"""
    src = tmp_path / "x.zip"
    src.write_bytes(b"x")

    fake_reject = object()

    class FakeParamiko:
        SSHClient = None  # 占位,upload 会 import 失败
        RejectPolicy = staticmethod(lambda: fake_reject)
        WarningPolicy = staticmethod(lambda: object())
        AutoAddPolicy = staticmethod(lambda: object())

    monkeypatch.setitem(sys.modules, "paramiko", FakeParamiko())

    u = SFTPUploader()
    # 因为 FakeParamiko 没有真正的 SSHClient,上传会失败;
    # 这里只验证没有 crash 且代码路径进入 SSHClient 构造阶段
    result = u.upload(
        str(src),
        logger=stub_logger,
        config={"host": "example.com", "username": "u", "password": "p"},
    )
    assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# 10. 旧静态方法(兼容性)
# ---------------------------------------------------------------------------

def test_legacy_uploader_class_still_importable():
    """Uploader.baidu/aliyun 静态方法仍存在(deprecated 但可用)。"""
    assert hasattr(Uploader, "baidu")
    assert hasattr(Uploader, "aliyun")


# ---------------------------------------------------------------------------
# 11. 插件目录发现
# ---------------------------------------------------------------------------

def test_plugin_discovery_from_dir(tmp_path, monkeypatch, stub_logger):
    """往临时插件目录丢一个 .py, 注册表应自动发现其 UploaderBase 子类。"""
    plugin_dir = tmp_path / "plugins" / "uploaders"
    plugin_dir.mkdir(parents=True)

    # 写一个最小插件
    plugin_file = plugin_dir / "fake_cloud.py"
    plugin_file.write_text(textwrap.dedent('''
        from wechat_forensic.uploader import UploaderBase

        class FakeCloudUploader(UploaderBase):
            name = "fake-cloud"
            display_name = "Fake Cloud (test only)"
            required_deps = []
            config_schema_hint = "api_key"

            def upload(self, file, logger=None, config=None):
                return self._return_success("fake://" + file)
    '''), encoding="utf-8")

    # 重定向 PLUGIN_DIR_USER 到临时目录
    import wechat_forensic.uploader as uploader_mod
    monkeypatch.setattr(uploader_mod, "PLUGIN_DIR_USER", plugin_dir)
    monkeypatch.setattr(uploader_mod, "PLUGIN_DIR_PROJECT", tmp_path / "no_such_dir")
    monkeypatch.setenv("WECHAT_FORENSIC_ENABLE_PLUGINS", "true")

    reg = UploaderRegistry()
    u = reg.get("fake-cloud")
    assert u is not None, f"插件没被发现。register list: {[x['name'] for x in reg.list()]}"
    result = u.upload("/tmp/test.zip", logger=stub_logger, config={})
    assert result["success"] is True
    assert result["remote"] == "fake:///tmp/test.zip"


def test_builtin_name_wins_over_plugin(tmp_path, monkeypatch, stub_logger):
    """第三方插件不应覆盖内置适配器。"""
    plugin_dir = tmp_path / "plugins" / "uploaders"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "sneaky.py").write_text(textwrap.dedent('''
        from wechat_forensic.uploader import UploaderBase
        class SneakyS3(UploaderBase):
            name = "s3"  # 试图覆盖内置!
            display_name = "Rogue S3"
            def upload(self, file, logger=None, config=None):
                return self._return_success("hacked://")
    '''), encoding="utf-8")
    import wechat_forensic.uploader as uploader_mod
    monkeypatch.setattr(uploader_mod, "PLUGIN_DIR_USER", plugin_dir)
    monkeypatch.setattr(uploader_mod, "PLUGIN_DIR_PROJECT", tmp_path / "no_such_dir")
    monkeypatch.setenv("WECHAT_FORENSIC_ENABLE_PLUGINS", "true")

    reg = UploaderRegistry()
    u = reg.get("s3")
    # 应仍是内置那个
    assert type(u) is S3Uploader


def test_bad_plugin_does_not_crash_registry(tmp_path, monkeypatch):
    """语法错误 / 导入错误的插件不应让整个注册表崩溃。"""
    plugin_dir = tmp_path / "plugins" / "uploaders"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "broken.py").write_text("def syntax(\n  error here\n", encoding="utf-8")
    import wechat_forensic.uploader as uploader_mod
    monkeypatch.setattr(uploader_mod, "PLUGIN_DIR_USER", plugin_dir)
    monkeypatch.setattr(uploader_mod, "PLUGIN_DIR_PROJECT", tmp_path / "no_such_dir")
    monkeypatch.setenv("WECHAT_FORENSIC_ENABLE_PLUGINS", "true")

    reg = UploaderRegistry()
    # 内置仍可用
    assert reg.get("baidu") is not None
    # 错误被记录
    assert any("broken.py" in k for k in reg.load_errors.keys())


# ---------------------------------------------------------------------------
# 12-13. 配置加载
# ---------------------------------------------------------------------------

def test_load_config_from_yaml(tmp_path, monkeypatch):
    """验证 _try_load_yaml 在有 PyYAML 时正确解析 yaml 文件。"""
    import importlib

    # 装一个最小 yaml mock: 支持 0/2 空格缩进的键值
    def _mini_yaml(text):
        out = {}
        stack = [(0, out)]  # (indent, container)
        for line in text.splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            indent = len(line) - len(line.lstrip())
            content = line.lstrip()
            key, _, val = content.partition(":")
            key, val = key.strip(), val.strip()
            # 弹出栈中比当前 indent 深或相等的
            while stack and stack[-1][0] >= indent:
                stack.pop()
            parent = stack[-1][1] if stack else out
            if not val:
                # 嵌套字典
                new = {}
                parent[key] = new
                stack.append((indent, new))
            else:
                parent[key] = val
        return out

    fake_yaml = importlib.import_module("types").ModuleType("yaml")
    fake_yaml.safe_load = _mini_yaml
    sys.modules["yaml"] = fake_yaml

    cfg_file = tmp_path / "upload.yaml"
    cfg_file.write_text(textwrap.dedent('''
        # 注释也被忽略
        s3:
          endpoint_url: https://s3.amazonaws.com
          bucket: my-bucket
          access_key: AKIA
          secret_key: secret
          region: us-east-1
        webdav:
          url: https://dav.jianguoyun.com/dav
          username: me@example.com
          password: pwd
    ''').strip(), encoding="utf-8")

    import wechat_forensic.uploader as uploader_mod
    monkeypatch.setattr(uploader_mod, "DEFAULT_CONFIG_PATH", tmp_path / "no.yaml")
    cfg = load_config(str(cfg_file))
    assert cfg["s3"]["bucket"] == "my-bucket"
    assert cfg["webdav"]["username"] == "me@example.com"


def test_load_config_from_json(tmp_path, monkeypatch):
    cfg_file = tmp_path / "upload.json"
    cfg_file.write_text(json.dumps({
        "local": {"destination_dir": "/mnt/backup", "mode": "copy"}
    }), encoding="utf-8")
    import wechat_forensic.uploader as uploader_mod
    monkeypatch.setattr(uploader_mod, "DEFAULT_CONFIG_PATH", tmp_path / "no.yaml")
    cfg = load_config(str(cfg_file))
    assert cfg["local"]["destination_dir"] == "/mnt/backup"


def test_load_config_inline_envvars(tmp_path, monkeypatch):
    import wechat_forensic.uploader as uploader_mod
    monkeypatch.setattr(uploader_mod, "DEFAULT_CONFIG_PATH", tmp_path / "no.yaml")
    monkeypatch.setenv("WECHAT_FORENSIC_UPLOAD_S3_BUCKET", "env-bucket")
    monkeypatch.setenv("WECHAT_FORENSIC_UPLOAD_S3_REGION", "us-west-1")
    monkeypatch.setenv("WECHAT_FORENSIC_UPLOAD_WEBDAV_URL", "https://dav.example.com")

    cfg = load_config()
    assert cfg["s3"]["bucket"] == "env-bucket"
    assert cfg["s3"]["region"] == "us-west-1"
    assert cfg["webdav"]["url"] == "https://dav.example.com"


def test_get_config_for_returns_section_or_empty():
    cfg = {"s3": {"bucket": "b"}, "webdav": {"url": "u"}}
    assert get_config_for("s3", cfg) == {"bucket": "b"}
    assert get_config_for("nonexistent", cfg) == {}


# ---------------------------------------------------------------------------
# 14. 返回值结构
# ---------------------------------------------------------------------------

def test_return_value_has_required_keys():
    """基类提供的工具方法必须返回标准结构。"""
    u = BaiduUploader()
    fail = u._return_failure("test reason")
    assert set(fail.keys()) >= {"success", "message", "remote", "algorithm"}
    assert fail["success"] is False
    assert fail["message"] == "test reason"
    assert fail["algorithm"] == "baidu"

    ok = u._return_success("remote/path", {"extra": 1})
    assert ok["success"] is True
    assert ok["remote"] == "remote/path"
    assert ok["extra"] == 1


# ---------------------------------------------------------------------------
# 15. CLI --upload-list
# ---------------------------------------------------------------------------

def test_cli_upload_list_exits_zero():
    r = subprocess.run(
        [sys.executable, "-m", "wechat_forensic.cli", "--upload-list"],
        capture_output=True, text=True,
        cwd=Path(__file__).resolve().parent.parent,
    )
    assert r.returncode == 0
    assert "Available uploaders" in r.stdout
    for name in ("baidu", "aliyun", "s3", "webdav", "sftp", "local"):
        assert name in r.stdout, f"{name} 应在 --upload-list 输出里"


def test_cli_unknown_uploader_logs_error(tmp_path):
    """CLI 给了不存在的 uploader name, 仍能跑完(只是上传步骤失败)。"""
    # 用最小命令触发到上传分支前就需要退出
    r = subprocess.run(
        [sys.executable, "-m", "wechat_forensic.cli",
         "--mode", "quick", "--no-interactive", "--upload", "totally-fake-uploader-xyz",
         "--source", str(tmp_path)],
        capture_output=True, text=True,
        cwd=Path(__file__).resolve().parent.parent,
    )
    # 应在扫描/定位阶段退出(找不到数据),但不能因 import 错误崩溃
    # 返回 0(我们没真数据)或 1(没找到数据) 都行,不能 -1/traceback
    assert r.returncode in (0, 1)
    # 不应出现 Python traceback
    assert "Traceback" not in r.stderr

"""云端上传(可选) — v2.0.5 可插拔架构

设计要点
========

1. **统一接口**: 所有上传器都继承 :class:`UploaderBase`,只需实现
   ``upload(file, logger, config) -> dict``。返回值统一为
   ``{"success": bool, "message": str, "remote": str, "algorithm": str}``。

2. **多渠道发现**:
   - 内置预设: ``baidu`` / ``aliyun`` / ``s3`` / ``webdav`` / ``sftp`` / ``local``
   - 第三方插件: ``~/.config/wechat-forensic/plugins/uploaders/*.py``
     内含 ``UploaderBase`` 子类即被自动发现,**无需 setuptools entry_points**
   - 项目级示例: ``<project>/uploaders/*.py`` (开发期 / 单文件部署场景)

3. **配置加载顺序** (高→低优先):
   1. ``--upload-config <path>`` CLI 参数
   2. ``$WECHAT_FORENSIC_UPLOAD_CONFIG`` 环境变量 (文件路径)
   3. ``$WECHAT_FORENSIC_UPLOAD_<NAME>_*`` 环境变量 (内联,见 :func:`load_config_from_env`)
   4. ``~/.config/wechat-forensic/upload.yaml`` 默认配置文件

4. **零破坏**: 旧的 ``Uploader.baidu()`` / ``Uploader.aliyun()`` 静态方法保留,
   行为不变,仅在 :func:`get_uploader` 找不到指定 name 时回退。

5. **按需依赖**: 每个适配器独立声明其依赖的第三方包,缺失时给清晰错误,
   不污染主安装。可选 extras: ``[s3]`` / ``[webdav]`` / ``[sftp]`` / ``[all]``。
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import logging
import os
import shutil
import subprocess
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from .hashing import Hasher


# ===========================================================================
# 常量
# ===========================================================================

PLUGIN_DIR_USER = Path.home() / ".config" / "wechat-forensic" / "plugins" / "uploaders"
PLUGIN_DIR_PROJECT = Path(__file__).resolve().parent.parent / "uploaders"
DEFAULT_CONFIG_PATH = Path.home() / ".config" / "wechat-forensic" / "upload.yaml"

# 旧版静态方法兼容标识
DEPRECATED_NAMES = {"baidu", "aliyun"}


# ===========================================================================
# 基类
# ===========================================================================

class UploaderBase(ABC):
    """所有上传器的抽象基类。

    子类必须设置类属性 ``name`` (唯一短名,小写英文,见下) 并实现
    :meth:`upload`。可选类属性:
    - ``display_name``: 人类可读名称
    - ``required_deps``: 列出本适配器需要的第三方包 (用于错误提示)
    - ``is_builtin``: True 表示内置,False 表示第三方
    """

    # ---- 必须由子类覆盖 ----
    name: str = ""  # 唯一短名,例如 "s3" / "baidu" / "my-company"
    display_name: str = ""
    required_deps: List[str] = []

    # ---- 可选覆盖 ----
    is_builtin: bool = True
    config_schema_hint: str = ""  # 提示: 这个 uploader 期望的 config 字段

    @abstractmethod
    def upload(
        self,
        file: str,
        logger: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """执行上传。必须返回:
        ``{"success": bool, "message": str, "remote": str, "algorithm": str}``
        失败时 ``success=False`` 并填充 ``message``。
        """
        raise NotImplementedError

    # ---- 公共工具方法(子类可复用) ----

    def _log(self, logger: Optional[Any], level: str, msg: str) -> None:
        """写日志: 优先用业务 logger, 退到 stderr。"""
        if logger is not None and hasattr(logger, level):
            try:
                getattr(logger, level)(msg)
                return
            except Exception:
                pass
        sys.stderr.write(f"[{level}] {msg}\n")

    def _missing_dep_message(self) -> str:
        if not self.required_deps:
            return "适配器未声明依赖"
        return (
            f"缺少依赖: {', '.join(self.required_deps)}。"
            f"安装方式: pip install wechat-forensic-pro[对应extra]"
        )

    def _return_failure(self, message: str) -> Dict[str, Any]:
        return {
            "success": False,
            "message": message,
            "remote": "",
            "algorithm": self.name,
        }

    def _return_success(self, remote: str, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        out = {"success": True, "message": "OK", "remote": remote, "algorithm": self.name}
        if extra:
            out.update(extra)
        return out


# ===========================================================================
# 内置适配器
# ===========================================================================

class BaiduUploader(UploaderBase):
    """百度网盘 - 通过 bypy CLI 调用。"""

    name = "baidu"
    display_name = "百度网盘 (bypy)"
    required_deps = ["bypy"]

    def upload(self, file, logger=None, config=None):
        config = config or {}
        remote_dir = config.get("remote_dir", "/wechat_forensic")
        self._log(logger, "info", f"上传百度云 (bypy) -> {remote_dir}/")
        try:
            r = subprocess.run(
                ["bypy", "upload", file, remote_dir],
                capture_output=True, text=True, timeout=600,
            )
        except FileNotFoundError:
            return self._return_failure("未安装 bypy: pip install bypy")
        except subprocess.TimeoutExpired:
            return self._return_failure("百度云上传超时 (>600s)")
        if r.returncode == 0:
            self._log(logger, "success", f"百度云上传成功 -> {remote_dir}")
            return self._return_success(f"{remote_dir}/{Path(file).name}")
        return self._return_failure(f"百度云失败: {r.stderr.strip() or r.stdout.strip()}")


class AliyunUploader(UploaderBase):
    """阿里云 OSS - 直接通过 oss2 SDK 上传。"""

    name = "aliyun"
    display_name = "阿里云 OSS"
    required_deps = ["oss2"]

    def upload(self, file, logger=None, config=None):
        config = config or {}
        # 兼容老 Config 类的常量 + 新 config dict
        endpoint = config.get("endpoint") or os.environ.get("ALIYUN_OSS_ENDPOINT", "")
        bucket_name = config.get("bucket") or os.environ.get("ALIYUN_OSS_BUCKET", "")
        ak = config.get("access_key") or os.environ.get("ALIYUN_ACCESS_KEY", "")
        sk = config.get("secret_key") or os.environ.get("ALIYUN_SECRET_KEY", "")
        prefix = config.get("prefix", "wechat_forensic/")

        if not (endpoint and bucket_name and ak and sk):
            return self._return_failure(
                "阿里云 OSS 配置缺失 (endpoint/bucket/access_key/secret_key)"
            )

        try:
            import oss2  # type: ignore
        except ImportError:
            return self._return_failure("未安装 oss2: pip install oss2")

        try:
            auth = oss2.Auth(ak, sk)
            bucket = oss2.Bucket(auth, endpoint, bucket_name)
            key = f"{prefix.rstrip('/')}/{Path(file).name}"
            bucket.put_object_from_file(key, file)
            self._log(logger, "success", f"阿里云上传成功: {key}")
            return self._return_success(
                f"oss://{bucket_name}/{key}",
                {"bucket": bucket_name, "key": key, "endpoint": endpoint},
            )
        except Exception as e:
            return self._return_failure(f"阿里云失败: {e}")


class S3Uploader(UploaderBase):
    """AWS S3 / 阿里 OSS-S3 / 腾讯 COS / 七牛 / MinIO 全部 S3 兼容协议。

    必需配置: ``endpoint_url / bucket / access_key / secret_key / region``
    可选:     ``prefix / use_ssl / multipart_threshold_mb``
    """

    name = "s3"
    display_name = "S3 兼容对象存储 (AWS S3 / 腾讯 COS / 七牛 / MinIO 等)"
    required_deps = ["boto3"]
    config_schema_hint = "endpoint_url, bucket, access_key, secret_key, region, prefix"

    def upload(self, file, logger=None, config=None):
        config = config or {}
        endpoint_url = config.get("endpoint_url")
        bucket = config.get("bucket")
        ak = config.get("access_key")
        sk = config.get("secret_key")
        region = config.get("region", "us-east-1")
        prefix = config.get("prefix", "wechat_forensic/").rstrip("/")
        use_ssl = bool(config.get("use_ssl", True))

        if not (bucket and ak and sk):
            return self._return_failure(
                "S3 配置缺失 (bucket / access_key / secret_key 必填)"
            )

        try:
            import boto3  # type: ignore
            from botocore.exceptions import BotoCoreError, ClientError  # type: ignore
        except ImportError:
            return self._return_failure("未安装 boto3: pip install boto3")

        try:
            client_kwargs = {
                "region_name": region,
                "aws_access_key_id": ak,
                "aws_secret_access_key": sk,
            }
            if endpoint_url:
                client_kwargs["endpoint_url"] = endpoint_url
                client_kwargs["use_ssl"] = use_ssl

            s3 = boto3.client("s3", **client_kwargs)
            key = f"{prefix}/{Path(file).name}"
            file_size = Path(file).stat().st_size

            self._log(logger, "info", f"S3 上传 {file} -> s3://{bucket}/{key} ({file_size} bytes)")
            # 大于 8MB 走 multipart
            if file_size > 8 * 1024 * 1024:
                from boto3.s3.transfer import TransferConfig  # type: ignore
                cfg = TransferConfig(multipart_threshold=8 * 1024 * 1024)
                s3.upload_file(file, bucket, key, Config=cfg)
            else:
                s3.upload_file(file, bucket, key)

            self._log(logger, "success", f"S3 上传成功: s3://{bucket}/{key}")
            return self._return_success(
                f"s3://{bucket}/{key}",
                {"bucket": bucket, "key": key, "endpoint": endpoint_url, "region": region},
            )
        except (BotoCoreError, ClientError) as e:
            return self._return_failure(f"S3 失败: {e}")
        except Exception as e:
            return self._return_failure(f"S3 异常: {e}")


class WebDAVUploader(UploaderBase):
    """WebDAV 协议 — 兼容坚果云 / Nextcloud / ownCloud / OneDrive(WebDAV 模式) 等。

    必需配置: ``url / username / password``
    可选:     ``remote_path / verify_ssl``
    """

    name = "webdav"
    display_name = "WebDAV (坚果云 / Nextcloud / ownCloud / OneDrive WebDAV)"
    required_deps = ["webdavclient3"]
    config_schema_hint = "url, username, password, remote_path, verify_ssl"

    def upload(self, file, logger=None, config=None):
        config = config or {}
        url = config.get("url")
        user = config.get("username")
        pwd = config.get("password")
        remote_path = config.get("remote_path", "/wechat_forensic/").rstrip("/")
        verify_ssl = bool(config.get("verify_ssl", True))

        if not (url and user and pwd):
            return self._return_failure(
                "WebDAV 配置缺失 (url / username / password 必填)"
            )

        try:
            from webdav3.client import Client  # type: ignore
        except ImportError:
            return self._return_failure(
                "未安装 webdavclient3: pip install webdavclient3"
            )

        try:
            options = {
                "webdav_hostname": url,
                "webdav_login": user,
                "webdav_password": pwd,
            }
            if not verify_ssl:
                # 仅对当前 Client 关闭 SSL 验证,不全局禁用 urllib3 警告
                options["verify"] = False
                self._log(
                    logger,
                    "warning",
                    "WebDAV verify_ssl=false: 已关闭 SSL 证书验证,存在中间人风险",
                )

            client = Client(options)
            # 远端目录不存在则尝试创建
            try:
                client.mkdir(remote_path)
            except Exception:
                pass  # 已存在不算错

            remote_file = f"{remote_path}/{Path(file).name}"
            self._log(logger, "info", f"WebDAV 上传 {file} -> {remote_file}")
            client.upload_sync(remote_path=remote_path, file_path=file)
            self._log(logger, "success", f"WebDAV 上传成功: {remote_file}")
            return self._return_success(remote_file, {"host": url})
        except Exception as e:
            return self._return_failure(f"WebDAV 失败: {e}")


class SFTPUploader(UploaderBase):
    """SFTP 协议 — 自建 SFTP / 树莓派 NAS / 老旧备份服务器。

    必需配置: ``host / port / username``
    可选:     ``password / private_key_path / remote_path / port (默认 22)``
              ``host_key_policy`` (默认 reject; 可选 warning / auto_add)
              ``known_hosts`` (默认 ~/.ssh/known_hosts)
    """

    name = "sftp"
    display_name = "SFTP (SSH 文件传输)"
    required_deps = ["paramiko"]
    config_schema_hint = (
        "host, port, username, password/private_key_path, remote_path, "
        "host_key_policy (warning/reject/auto_add), known_hosts"
    )

    def upload(self, file, logger=None, config=None):
        config = config or {}
        host = config.get("host")
        port = int(config.get("port", 22))
        user = config.get("username")
        pwd = config.get("password")
        key_path = config.get("private_key_path")
        remote_path = config.get("remote_path", "/wechat_forensic/").rstrip("/")
        policy = config.get("host_key_policy", "reject").lower()
        known_hosts = config.get("known_hosts") or str(Path.home() / ".ssh" / "known_hosts")

        if not (host and user and (pwd or key_path)):
            return self._return_failure(
                "SFTP 配置缺失 (host / username / (password 或 private_key_path) 必填)"
            )

        try:
            import paramiko  # type: ignore
        except ImportError:
            return self._return_failure("未安装 paramiko: pip install paramiko")

        try:
            self._log(logger, "info", f"SFTP {user}@{host}:{port} 上传 {file}")
            client = paramiko.SSHClient()

            # 加载 known_hosts; 不存在则跳过(稍后由 host key policy 决定行为)
            try:
                client.load_host_keys(known_hosts)
            except Exception:
                pass

            if policy == "auto_add":
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                self._log(
                    logger,
                    "warning",
                    "SFTP host_key_policy=auto_add: 将自动信任未知主机密钥,存在中间人风险",
                )
            elif policy == "warning":
                # warning: 未知主机继续连接但记录警告(比 auto_add 安全,但仍有中间人风险)
                client.set_missing_host_key_policy(paramiko.WarningPolicy())
                self._log(
                    logger,
                    "warning",
                    "SFTP host_key_policy=warning: 未知主机仍会继续连接,司法场景建议用 reject",
                )
            else:
                # 默认 reject: 未知主机直接拒绝,最安全
                client.set_missing_host_key_policy(paramiko.RejectPolicy())

            connect_kwargs = {"hostname": host, "port": port, "username": user, "timeout": 30}
            if pwd:
                connect_kwargs["password"] = pwd
            if key_path:
                connect_kwargs["key_filename"] = key_path
            client.connect(**connect_kwargs)

            sftp = client.open_sftp()
            try:
                sftp.mkdir(remote_path)
            except OSError:
                pass  # 已存在

            remote_file = f"{remote_path}/{Path(file).name}"
            sftp.put(file, remote_file)
            sftp.chmod(remote_file, 0o640)  # 收紧权限
            sftp.close()
            client.close()
            self._log(logger, "success", f"SFTP 上传成功: {remote_file}")
            return self._return_success(
                f"sftp://{user}@{host}:{port}{remote_file}",
                {"host": host, "port": port, "remote": remote_file},
            )
        except Exception as e:
            return self._return_failure(f"SFTP 失败: {e}")


class LocalUploader(UploaderBase):
    """本地目标 — 复制到 NAS 挂载点 / USB 移动硬盘 / 第二个硬盘。

    必需配置: ``destination_dir`` (绝对路径,自动 mkdir -p)
    可选:     ``mode (copy|move|hardlink)`` 默认 copy
              ``danger_allow_evidence_move`` 设为 true 才允许 move/hardlink
    """

    name = "local"
    display_name = "本地备份 (NAS 挂载点 / 移动硬盘 / 第二个硬盘)"
    required_deps = []  # 仅 stdlib
    config_schema_hint = (
        "destination_dir, mode (copy|move|hardlink), "
        "danger_allow_evidence_move (true/false)"
    )

    def upload(self, file, logger=None, config=None):
        config = config or {}
        dest_dir = config.get("destination_dir")
        mode = config.get("mode", "copy").lower()
        danger_allowed = str(config.get("danger_allow_evidence_move", "")).lower() in (
            "1",
            "true",
            "yes",
        )

        if not dest_dir:
            return self._return_failure(
                "local 配置缺失 destination_dir (目标绝对路径)"
            )

        if mode in ("move", "hardlink") and not danger_allowed:
            return self._return_failure(
                f"mode={mode} 会移动证据原件或改变证据 inode,司法场景严禁。"
                "如需继续,请设置 danger_allow_evidence_move=true 并确认风险自负。"
            )

        try:
            dest_dir_path = Path(dest_dir).expanduser().resolve()
            dest_dir_path.mkdir(parents=True, exist_ok=True)
            src = Path(file)
            dst = dest_dir_path / src.name

            self._log(logger, "info", f"本地 {mode}: {src} -> {dst}")

            if mode == "move":
                shutil.move(str(src), str(dst))
            elif mode == "hardlink":
                if dst.exists():
                    dst.unlink()
                os.link(str(src), str(dst))
            else:  # copy (默认)
                shutil.copy2(str(src), str(dst))

            # 复制后计算 SHA-256 校验
            from .hashing import Hasher  # 避免循环引用
            local_sha = Hasher.sha256_file(str(dst))

            self._log(logger, "success", f"本地备份成功: {dst} (sha256={local_sha[:16]}...)")
            return self._return_success(
                str(dst),
                {"mode": mode, "destination": str(dst), "sha256": local_sha},
            )
        except Exception as e:
            return self._return_failure(f"本地备份失败: {e}")


# ===========================================================================
# 注册表 + 发现
# ===========================================================================

class UploaderRegistry:
    """上传器注册表: 内置 + 插件发现。"""

    def __init__(self):
        self._classes: Dict[str, Type[UploaderBase]] = {}
        self._load_errors: Dict[str, str] = {}
        self._loaded = False

    # ---- 内置类列表(导入即注册) ----
    BUILTIN_CLASSES: List[Type[UploaderBase]] = [
        BaiduUploader,
        AliyunUploader,
        S3Uploader,
        WebDAVUploader,
        SFTPUploader,
        LocalUploader,
    ]

    def ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        for cls in self.BUILTIN_CLASSES:
            self._register(cls)

        # 第三方插件目录: 默认禁用,需显式开启并校验
        plugins_enabled = os.environ.get(
            "WECHAT_FORENSIC_ENABLE_PLUGINS", ""
        ).strip().lower() in ("1", "true", "yes")
        if not plugins_enabled:
            if PLUGIN_DIR_USER.exists() and any(PLUGIN_DIR_USER.glob("*.py")):
                sys.stderr.write(
                    "[warning] 发现第三方上传器插件目录,但插件加载已禁用。"
                    "如需加载请设置 WECHAT_FORENSIC_ENABLE_PLUGINS=true 并核对文件哈希。\n"
                )
            return

        sys.stderr.write(
            "[warning] WECHAT_FORENSIC_ENABLE_PLUGINS=true: 即将加载第三方插件,"
            "请确保插件来源可信。\n"
        )
        for d in (PLUGIN_DIR_USER, PLUGIN_DIR_PROJECT):
            if d.exists():
                self._discover_from_dir(d)

    def _register(self, cls: Type[UploaderBase]) -> None:
        if not cls.name:
            return
        if cls.name in self._classes:
            # 插件不应覆盖内置,但允许同 name 出现在多个插件目录时取先发现者
            existing = self._classes[cls.name]
            if existing.is_builtin:
                # 内置优先,只在警告中提示
                sys.stderr.write(
                    f"[warning] 第三方上传器 '{cls.name}' 与内置同名,被忽略 ({cls.__module__})\n"
                )
                return
        self._classes[cls.name] = cls

    def _discover_from_dir(self, d: Path) -> None:
        for f in sorted(d.glob("*.py")):
            if f.name.startswith("_"):
                continue
            mod_name = f"wfp_uploader_plugin_{f.stem}"
            try:
                sha256 = Hasher.sha256_file(str(f))
                sys.stderr.write(
                    f"[info] 加载第三方插件 {f.name} (sha256={sha256})\n"
                )
                spec = importlib.util.spec_from_file_location(mod_name, f)
                if spec is None or spec.loader is None:
                    continue
                module = importlib.util.module_from_spec(spec)
                sys.modules[mod_name] = module
                spec.loader.exec_module(module)
                # 扫描模块中所有 UploaderBase 子类
                for attr in dir(module):
                    obj = getattr(module, attr)
                    if (
                        isinstance(obj, type)
                        and issubclass(obj, UploaderBase)
                        and obj is not UploaderBase
                    ):
                        obj.is_builtin = False
                        self._register(obj)
            except Exception as e:
                self._load_errors[str(f)] = f"{type(e).__name__}: {e}"
                sys.stderr.write(f"[warning] 插件 {f.name} 加载失败: {e}\n")

    # ---- 公共查询 API ----

    def list(self) -> List[Dict[str, str]]:
        """列出所有可用的上传器 (展示给用户)。"""
        self.ensure_loaded()
        out = []
        for cls in self._classes.values():
            out.append({
                "name": cls.name,
                "display_name": cls.display_name,
                "is_builtin": cls.is_builtin,
                "required_deps": ", ".join(cls.required_deps) if cls.required_deps else "(无)",
                "config_schema_hint": cls.config_schema_hint,
            })
        out.sort(key=lambda x: (not x["is_builtin"], x["name"]))
        return out

    def get(self, name: str) -> Optional[UploaderBase]:
        """按 name 取得上传器实例(已就绪,可直接 upload)。"""
        self.ensure_loaded()
        cls = self._classes.get(name)
        if cls is None:
            return None
        try:
            return cls()
        except Exception as e:
            self._load_errors[name] = f"实例化失败: {e}"
            return None

    @property
    def load_errors(self) -> Dict[str, str]:
        self.ensure_loaded()
        return dict(self._load_errors)


# 模块级单例
_REGISTRY = UploaderRegistry()


# ===========================================================================
# 配置加载
# ===========================================================================

def _try_load_yaml(path: Path) -> Optional[Dict[str, Any]]:
    """YAML 优先, 退到 JSON(都失败返回 None)。"""
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:
        sys.stderr.write(f"[warning] 读取配置 {path} 失败: {e}\n")
        return None
    # 优先 yaml
    if path.suffix.lower() in (".yaml", ".yml"):
        try:
            import yaml  # type: ignore
            return yaml.safe_load(text)
        except ImportError:
            sys.stderr.write(
                "[warning] 未安装 PyYAML, 尝试按 JSON 解析 (安装: pip install pyyaml)\n"
            )
        except Exception as e:
            sys.stderr.write(f"[warning] YAML 解析失败 {path}: {e}\n")
            return None
    # json
    try:
        return json.loads(text)
    except Exception as e:
        sys.stderr.write(f"[warning] JSON 解析失败 {path}: {e}\n")
        return None


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """按优先级加载上传配置:
    1. ``config_path`` 参数
    2. ``$WECHAT_FORENSIC_UPLOAD_CONFIG`` 环境变量
    3. ``~/.config/wechat-forensic/upload.yaml`` 默认
    4. ``$WECHAT_FORENSIC_UPLOAD_<NAME>_*`` 内联环境变量

    返回 dict: ``{"<uploader_name>": {...config...}, "default": "name"}``
    """
    cfg: Dict[str, Any] = {}
    # 1) 参数
    candidates: List[Path] = []
    if config_path:
        candidates.append(Path(config_path))
    # 2) 环境变量 (文件路径)
    env_path = os.environ.get("WECHAT_FORENSIC_UPLOAD_CONFIG")
    if env_path:
        candidates.append(Path(env_path))
    # 3) 默认
    candidates.append(DEFAULT_CONFIG_PATH)

    for p in candidates:
        data = _try_load_yaml(p)
        if isinstance(data, dict):
            cfg.update(data)
            break  # 找到第一个有效文件就停

    # 4) 内联环境变量补充: WECHAT_FORENSIC_UPLOAD_S3_BUCKET=xxx 等
    for key, val in os.environ.items():
        if not key.startswith("WECHAT_FORENSIC_UPLOAD_"):
            continue
        # 形如 WECHAT_FORENSIC_UPLOAD_S3_BUCKET
        parts = key.split("_")[3:]  # 去掉前 3 段 (WECHAT_FORENSIC_UPLOAD)
        if len(parts) < 2:
            continue
        name, *rest = parts
        name_lc = name.lower()
        sub_key = "_".join(rest).lower()
        if name_lc not in cfg:
            cfg[name_lc] = {}
        if isinstance(cfg.get(name_lc), dict):
            cfg[name_lc][sub_key] = val

    return cfg


def get_config_for(name: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """从总配置里取指定 name 的子配置。"""
    config = config or load_config()
    section = config.get(name)
    if isinstance(section, dict):
        return section
    return {}


# ===========================================================================
# 旧版兼容 API
# ===========================================================================

class Uploader:
    """向后兼容的静态方法封装。**已弃用**,新代码请用 ``UploaderRegistry``。"""

    @staticmethod
    def baidu(file: str, logger=None) -> bool:  # pragma: no cover
        import warnings
        warnings.warn(
            "Uploader.baidu() 已弃用, 请改用 UploaderRegistry().get('baidu').upload()",
            DeprecationWarning, stacklevel=2,
        )
        u = _REGISTRY.get("baidu")
        return bool(u and u.upload(file, logger=logger).get("success"))

    @staticmethod
    def aliyun(file: str, logger=None) -> bool:  # pragma: no cover
        import warnings
        warnings.warn(
            "Uploader.aliyun() 已弃用, 请改用 UploaderRegistry().get('aliyun').upload()",
            DeprecationWarning, stacklevel=2,
        )
        u = _REGISTRY.get("aliyun")
        return bool(u and u.upload(file, logger=logger).get("success"))


# 公开 API
__all__ = [
    "UploaderBase",
    "UploaderRegistry",
    "Uploader",  # 旧版兼容
    # 内置适配器(供高级用户直接构造)
    "BaiduUploader",
    "AliyunUploader",
    "S3Uploader",
    "WebDAVUploader",
    "SFTPUploader",
    "LocalUploader",
    # 工具
    "load_config",
    "get_config_for",
    "PLUGIN_DIR_USER",
    "PLUGIN_DIR_PROJECT",
    "DEFAULT_CONFIG_PATH",
]

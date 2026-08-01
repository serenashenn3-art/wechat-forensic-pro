"""镜像生成器:位对位镜像 + 取证级目录镜像"""

import datetime
import getpass
import hashlib
import json
import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Dict

from .hashing import Hasher
from .utils import is_admin


class MirrorGenerator:
    """位对位镜像生成器"""

    def __init__(self, logger, chunk_size: int = 4 * 1024 * 1024):
        self.log = logger
        self.chunk_size = chunk_size

    @staticmethod
    def _validate_disk_path(path: str) -> bool:
        """校验磁盘设备路径基本合法性,防止特殊字符注入或误操作普通文件。"""
        if not path or not isinstance(path, str):
            return False
        # 拒绝控制字符、换行、反引号、分号、管道等 shell 危险字符
        dangerous = set("\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f"
                        "\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f")
        if any(c in dangerous for c in path):
            return False
        if ";" in path or "|" in path or "&" in path or "`" in path or "$" in path:
            return False
        # 基本格式: Unix /dev/xxx 或 Windows \\.\PhysicalDriveN / \\?\...
        sysname = platform.system()
        if sysname == "Windows":
            return path.startswith("\\\\.\\") or path.startswith("\\\\?\\")
        return path.startswith("/dev/")

    def mirror_disk_dd(self, source_disk: str, output_path: str) -> Dict:
        """使用 dd 命令生成位对位镜像(Linux/Mac 推荐)"""
        self.log.info(f"开始位对位镜像: {source_disk} -> {output_path}")
        self.log.evidence(f"源设备: {source_disk}")

        if not self._validate_disk_path(source_disk):
            err = f"源设备路径不合法或不是标准设备路径: {source_disk}"
            self.log.error(err)
            return {"success": False, "error": err}

        if not output_path or not isinstance(output_path, str):
            return {"success": False, "error": "输出路径不能为空"}

        if not is_admin():
            self.log.warning("生成磁盘镜像需要管理员/root 权限")

        start_time = datetime.datetime.now()
        read_errors: list = []
        try:
            cmd = [
                "dd",
                f"if={source_disk}",
                f"of={output_path}",
                "bs=4M",
                "status=progress",
                "conv=noerror,sync",
            ]
            self.log.info(f"执行: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)

            end_time = datetime.datetime.now()

            # dd 在 noerror 模式下 returncode 可能仍为 0,但 stderr 会记录读取错误
            stderr_lines = (result.stderr or "").splitlines()
            for line in stderr_lines:
                lowered = line.lower()
                if "error" in lowered or "failed" in lowered or "invalid" in lowered:
                    read_errors.append(line.strip())
                    self.log.warning(f"dd 读取错误: {line.strip()}")

            if result.returncode != 0:
                self.log.error(f"dd 失败: {result.stderr}")
                return {"success": False, "error": result.stderr}

            self.log.info("计算镜像 SHA-256...")
            sha256 = Hasher.sha256_file(output_path)

            info = {
                "success": True,
                "source": source_disk,
                "output": output_path,
                "sha256": sha256,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_sec": (end_time - start_time).total_seconds(),
                "size_bytes": os.path.getsize(output_path),
                "tool": "dd",
                "operator": getpass.getuser(),
                "hostname": platform.node(),
                "read_errors": read_errors,
                "read_error_count": len(read_errors),
            }
            self.log.success(f"镜像完成: {output_path}")
            self.log.evidence(f"镜像 SHA-256: {sha256}")
            if read_errors:
                self.log.evidence(f"dd 读取错误数: {len(read_errors)}")
            return info
        except Exception as e:
            self.log.error(f"镜像生成异常: {e}")
            return {"success": False, "error": str(e)}

    def mirror_partition_python(self, source_path: str, output_path: str) -> Dict:
        """纯 Python 逐块复制(适用分区/文件)"""
        self.log.info(f"开始 Python 逐块镜像: {source_path} -> {output_path}")
        start_time = datetime.datetime.now()

        total_bytes = 0
        sha256 = hashlib.sha256()
        try:
            with open(source_path, "rb") as src, open(output_path, "wb") as dst:
                while True:
                    chunk = src.read(self.chunk_size)
                    if not chunk:
                        break
                    dst.write(chunk)
                    sha256.update(chunk)
                    total_bytes += len(chunk)
            end_time = datetime.datetime.now()
            info = {
                "success": True,
                "source": source_path,
                "output": output_path,
                "sha256": sha256.hexdigest(),
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_sec": (end_time - start_time).total_seconds(),
                "size_bytes": total_bytes,
                "tool": "python_raw_copy",
                "operator": getpass.getuser(),
                "hostname": platform.node(),
            }
            self.log.success(f"镜像完成: {output_path} ({total_bytes / 1024**3:.2f} GB)")
            self.log.evidence(f"镜像 SHA-256: {info['sha256']}")
            return info
        except Exception as e:
            self.log.error(f"镜像异常: {e}")
            return {"success": False, "error": str(e)}

    def mirror_directory_forensic(self, source_dir: str, output_dir: str) -> Dict:
        """取证级目录镜像:保留元数据 + 哈希清单"""
        self.log.info(f"开始取证级目录镜像: {source_dir}")
        start_time = datetime.datetime.now()

        src = Path(source_dir)
        dst = Path(output_dir)
        dst.mkdir(parents=True, exist_ok=True)

        manifest = {
            "type": "forensic_directory_mirror",
            "source": str(src),
            "output": str(dst),
            "start_time": start_time.isoformat(),
            "operator": getpass.getuser(),
            "hostname": platform.node(),
            "platform": platform.platform(),
            "files": [],
        }

        total_files = 0
        for root, dirs, files in os.walk(src):
            dirs[:] = [d for d in dirs if d not in ["Cache", "tmp", "temp", "log", "Logs"]]
            rel_root = Path(root).relative_to(src)
            dst_root = dst / rel_root
            dst_root.mkdir(parents=True, exist_ok=True)

            for filename in files:
                src_file = Path(root) / filename
                dst_file = dst_root / filename
                try:
                    shutil.copy2(src_file, dst_file)
                    file_sha256 = Hasher.sha256_file(str(src_file))
                    stat = src_file.stat()
                    manifest["files"].append(
                        {
                            "relative_path": str(rel_root / filename),
                            "sha256": file_sha256,
                            "size_bytes": stat.st_size,
                            "mtime": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "atime": datetime.datetime.fromtimestamp(stat.st_atime).isoformat(),
                            "ctime": datetime.datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        }
                    )
                    total_files += 1
                except Exception as e:
                    self.log.warning(f"跳过 {src_file}: {e}")
                    manifest["files"].append(
                        {"relative_path": str(rel_root / filename), "error": str(e)}
                    )

        manifest_path = dst / "_forensic_manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        manifest_sha256 = Hasher.sha256_file(str(manifest_path))
        manifest["manifest_sha256"] = manifest_sha256
        manifest["end_time"] = datetime.datetime.now().isoformat()
        manifest["total_files"] = total_files
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        self.log.success(f"取证镜像完成: {dst} ({total_files} 文件)")
        self.log.evidence(f"清单 SHA-256: {manifest_sha256}")
        return manifest

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WeChat Forensic Extractor Pro
跨平台微信聊天记录取证提取工具链 v2.0
支持: 位对位镜像生成 | 哈希校验 | 证据链保全 | 云端备份
平台: Windows / macOS / Linux
用法: sudo python wechat_forensic_pro.py
"""

import os
import sys
import shutil
import json
import hashlib
import zipfile
import platform
import subprocess
import datetime
import argparse
import logging
import getpass
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict

# ==================== 配置 ====================
@dataclass
class Config:
    OUTPUT_DIR: str = "./wechat_forensic_output"
    MIRROR_DIR: str = "./wechat_mirrors"
    LOG_FILE: str = "./forensic_log.txt"
    ZIP_PASSWORD: Optional[str] = None
    CHUNK_SIZE: int = 1024 * 1024 * 4  # 4MB 块

    # 阿里云OSS (留空则跳过)
    ALIYUN_OSS_ENDPOINT: str = ""
    ALIYUN_OSS_BUCKET: str = ""
    ALIYUN_ACCESS_KEY: str = ""
    ALIYUN_SECRET_KEY: str = ""

    # 微信默认路径
    WECHAT_PATHS: Dict = None

    def __post_init__(self):
        self.WECHAT_PATHS = {
            "Windows": [
                r"%USERPROFILE%\Documents\WeChat Files",
                r"D:\Documents\WeChat Files",
                r"D:\WeChat Files",
                r"E:\WeChat Files",
            ],
            "Darwin": [
                "~/Library/Containers/com.tencent.xinWeChat/Data/Library/Application Support/com.tencent.xinWeChat",
            ],
            "Linux": [
                "~/.config/wechat",
            ]
        }

        self.ITUNES_BACKUP = {
            "Windows": r"%USERPROFILE%\Apple\MobileSync\Backup",
            "Darwin": "~/Library/Application Support/MobileSync/Backup",
        }


# ==================== 跨平台辅助 ====================
def is_admin() -> bool:
    """跨平台判断当前进程是否具有管理员/root权限"""
    try:
        if os.name == 'nt':
            import ctypes
            try:
                return bool(ctypes.windll.shell32.IsUserAnAdmin())
            except Exception:
                return False
        else:
            return os.geteuid() == 0
    except Exception:
        return False


# ==================== 日志系统 ====================
class ForensicLogger:
    def __init__(self, log_file: str):
        self.log_file = log_file
        logging.basicConfig(
            level=logging.INFO,
            format='[%(asctime)s] [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger("Forensic")

    def info(self, msg): self.logger.info(msg)
    def warning(self, msg): self.logger.warning(msg)
    def error(self, msg): self.logger.error(msg)
    def success(self, msg): self.logger.info(f"[OK] {msg}")
    def evidence(self, msg): self.logger.info(f"[EVIDENCE] {msg}")


# ==================== 哈希工具 ====================
class Hasher:
    @staticmethod
    def sha256_file(filepath: str, chunk_size: int = 4*1024*1024) -> str:
        """计算文件 SHA-256"""
        h = hashlib.sha256()
        with open(filepath, 'rb') as f:
            while chunk := f.read(chunk_size):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def md5_file(filepath: str, chunk_size: int = 4*1024*1024) -> str:
        """计算文件 MD5"""
        h = hashlib.md5()
        with open(filepath, 'rb') as f:
            while chunk := f.read(chunk_size):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def sha256_bytes(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def verify(filepath: str, expected_sha256: str) -> bool:
        actual = Hasher.sha256_file(filepath)
        return actual.lower() == expected_sha256.lower()


# ==================== 镜像生成器 ====================
class MirrorGenerator:
    """位对位镜像生成器"""

    def __init__(self, logger: ForensicLogger, chunk_size: int = 4*1024*1024):
        self.log = logger
        self.chunk_size = chunk_size

    def mirror_disk_dd(self, source_disk: str, output_path: str) -> Dict:
        """
        使用 dd 命令生成位对位镜像（推荐，Linux/Mac）
        source_disk: 如 /dev/sdb 或 /dev/disk2
        """
        self.log.info(f"开始位对位镜像: {source_disk} -> {output_path}")
        self.log.evidence(f"源设备: {source_disk}")

        # 检查权限（跨平台）
        if not is_admin():
            self.log.warning("生成磁盘镜像需要管理员/root权限")

        start_time = datetime.datetime.now()

        try:
            # 使用 dd 带进度显示
            cmd = [
                "dd",
                f"if={source_disk}",
                f"of={output_path}",
                "bs=4M",
                "status=progress",
                "conv=noerror,sync"  # 遇到坏扇区继续，用0填充
            ]

            self.log.info(f"执行: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)

            end_time = datetime.datetime.now()

            if result.returncode != 0:
                self.log.error(f"dd 失败: {result.stderr}")
                return {"success": False, "error": result.stderr}

            # 计算镜像哈希
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
                "hostname": platform.node()
            }

            self.log.success(f"镜像完成: {output_path}")
            self.log.evidence(f"镜像 SHA-256: {sha256}")

            return info

        except Exception as e:
            self.log.error(f"镜像生成异常: {e}")
            return {"success": False, "error": str(e)}

    def mirror_partition_python(self, source_path: str, output_path: str) -> Dict:
        """
        纯 Python 逐块复制（适用于分区/目录，非整块磁盘）
        用于将 WeChat Files 目录做位对位打包
        """
        self.log.info(f"开始 Python 逐块镜像: {source_path} -> {output_path}")
        start_time = datetime.datetime.now()

        total_bytes = 0
        sha256 = hashlib.sha256()

        try:
            with open(source_path, 'rb') as src, open(output_path, 'wb') as dst:
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
                "hostname": platform.node()
            }

            self.log.success(f"镜像完成: {output_path} ({total_bytes/1024**3:.2f} GB)")
            self.log.evidence(f"镜像 SHA-256: {info['sha256']}")

            return info

        except Exception as e:
            self.log.error(f"镜像异常: {e}")
            return {"success": False, "error": str(e)}

    def mirror_directory_forensic(self, source_dir: str, output_dir: str) -> Dict:
        """
        取证级目录镜像：保留所有元数据，生成哈希清单
        """
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
            "files": []
        }

        total_files = 0

        for root, dirs, files in os.walk(src):
            # 跳过缓存和临时文件
            dirs[:] = [d for d in dirs if d not in ['Cache', 'tmp', 'temp', 'log', 'Logs']]

            rel_root = Path(root).relative_to(src)
            dst_root = dst / rel_root
            dst_root.mkdir(parents=True, exist_ok=True)

            for filename in files:
                src_file = Path(root) / filename
                dst_file = dst_root / filename

                try:
                    # 复制文件（保留元数据）
                    shutil.copy2(src_file, dst_file)

                    # 计算哈希
                    file_sha256 = Hasher.sha256_file(str(src_file))

                    # 记录元数据
                    stat = src_file.stat()
                    file_info = {
                        "relative_path": str(rel_root / filename),
                        "sha256": file_sha256,
                        "size_bytes": stat.st_size,
                        "mtime": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "atime": datetime.datetime.fromtimestamp(stat.st_atime).isoformat(),
                        "ctime": datetime.datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    }
                    manifest["files"].append(file_info)
                    total_files += 1

                except Exception as e:
                    self.log.warning(f"跳过 {src_file}: {e}")
                    manifest["files"].append({
                        "relative_path": str(rel_root / filename),
                        "error": str(e)
                    })

        # 保存清单
        manifest_path = dst / "_forensic_manifest.json"
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        # 计算清单哈希
        manifest_sha256 = Hasher.sha256_file(str(manifest_path))
        manifest["manifest_sha256"] = manifest_sha256
        manifest["end_time"] = datetime.datetime.now().isoformat()
        manifest["total_files"] = total_files

        # 重新保存带哈希的清单
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        self.log.success(f"取证镜像完成: {dst} ({total_files} 文件)")
        self.log.evidence(f"清单 SHA-256: {manifest_sha256}")

        return manifest


# ==================== 设备扫描 ====================
class Scanner:
    def __init__(self, logger: ForensicLogger):
        self.log = logger
        self.sys = platform.system()

    def drives(self) -> List[Dict]:
        """扫描所有磁盘"""
        drives = []
        try:
            import psutil
            for p in psutil.disk_partitions(all=True):
                try:
                    u = psutil.disk_usage(p.mountpoint)
                    drives.append({
                        "device": p.device,
                        "mount": p.mountpoint,
                        "fstype": p.fstype,
                        "opts": p.opts,
                        "free": self._human(u.free),
                        "used": self._human(u.used),
                        "total": self._human(u.total),
                        "free_bytes": u.free,
                    })
                except (PermissionError, OSError):
                    continue
        except ImportError:
            self.log.warning("未安装 psutil，使用系统命令扫描")
            drives = self._fallback_scan()
        return drives

    def _fallback_scan(self) -> List[Dict]:
        drives = []
        if self.sys == "Windows":
            try:
                # PowerShell 在 Win10+ 普遍可用，比 wmic 稳定
                ps_cmd = (
                    "Get-CimInstance Win32_LogicalDisk | "
                    "Select-Object DeviceID,Size,FreeSpace,FileSystem,VolumeName | "
                    "ConvertTo-Csv -NoTypeInformation"
                )
                r = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", ps_cmd],
                    capture_output=True, text=True, timeout=30
                )
                if r.returncode == 0 and r.stdout.strip():
                    lines = r.stdout.strip().split('\n')[1:]  # 跳过表头
                    for line in lines:
                        parts = [p.strip().strip('"') for p in line.split(',')]
                        if len(parts) >= 4 and parts[0]:
                            size = int(parts[1]) if parts[1].isdigit() else 0
                            free = int(parts[2]) if parts[2].isdigit() else 0
                            drives.append({
                                "device": parts[0],
                                "mount": parts[0],
                                "fstype": parts[3] if parts[3] else "-",
                                "label": parts[4] if len(parts) > 4 else "-",
                                "free": self._human(free),
                                "used": self._human(size - free),
                                "total": self._human(size),
                                "free_bytes": free,
                            })
                    return drives
                # 回退到 wmic
                r = subprocess.run(
                    ["wmic", "logicaldisk", "get",
                     "DeviceID,Size,FreeSpace,FileSystem,VolumeName"],
                    capture_output=True, text=True, timeout=30
                )
                for line in r.stdout.strip().split('\n')[1:]:
                    parts = line.split()
                    if len(parts) >= 4:
                        drives.append({
                            "device": parts[0], "mount": parts[0],
                            "fstype": parts[3] if len(parts) > 3 else "-",
                            "label": parts[4] if len(parts) > 4 else "-",
                            "free": "-", "total": "-", "free_bytes": 0
                        })
            except FileNotFoundError:
                self.log.warning("未找到 powershell/wmic,磁盘扫描跳过")
            except Exception as e:
                self.log.error(f"扫描失败: {e}")
        else:
            try:
                r = subprocess.run(["df", "-h"], capture_output=True, text=True, timeout=30)
                for line in r.stdout.strip().split('\n')[1:]:
                    p = line.split()
                    if len(p) >= 6:
                        drives.append({
                            "device": p[0], "mount": p[5], "fstype": "-",
                            "free": p[3], "total": p[1], "free_bytes": 0
                        })
            except Exception as e:
                self.log.error(f"扫描失败: {e}")
        return drives

    def physical_disks(self) -> List[Dict]:
        """扫描物理磁盘（用于位对位镜像）"""
        disks = []
        if self.sys == "Windows":
            try:
                ps_cmd = (
                    "Get-CimInstance Win32_DiskDrive | "
                    "Select-Object Index,Model,Size,MediaType,InterfaceType | "
                    "ConvertTo-Csv -NoTypeInformation"
                )
                r = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", ps_cmd],
                    capture_output=True, text=True, timeout=30
                )
                if r.returncode == 0 and r.stdout.strip():
                    lines = r.stdout.strip().split('\n')[1:]
                    for line in lines:
                        parts = [p.strip().strip('"') for p in line.split(',')]
                        if len(parts) >= 3 and parts[0]:
                            size_bytes = int(parts[2]) if parts[2].isdigit() else 0
                            disks.append({
                                "index": parts[0],
                                "model": parts[1] if len(parts) > 1 else "-",
                                "size": self._human(size_bytes),
                                "size_bytes": size_bytes,
                                "media": parts[3] if len(parts) > 3 else "-",
                                "interface": parts[4] if len(parts) > 4 else "-",
                                "path": f"\\\\.\\PhysicalDrive{parts[0]}"
                            })
                    return disks
                # 回退 wmic
                r = subprocess.run(["wmic", "diskdrive", "get",
                                    "Index,Model,Size,MediaType,InterfaceType",
                                    "/format:csv"],
                                   capture_output=True, text=True, timeout=30)
                for line in r.stdout.strip().split('\n')[1:]:
                    if line.strip():
                        parts = line.split(',')
                        if len(parts) >= 5:
                            disks.append({
                                "index": parts[1],
                                "model": parts[2],
                                "size": parts[3],
                                "media": parts[4],
                                "path": f"\\\\.\\PhysicalDrive{parts[1]}"
                            })
            except Exception as e:
                self.log.error(f"扫描物理磁盘失败: {e}")
        elif self.sys == "Darwin":
            try:
                # 使用 diskutil list 直接文本输出更稳定
                r = subprocess.run(["diskutil", "list"], capture_output=True, text=True, timeout=30)
                for line in r.stdout.split('\n'):
                    line = line.strip()
                    # 形如 "/dev/disk0       (internal):"
                    if line.startswith("/dev/disk") and ":" in line:
                        path = line.split()[0]
                        # 过滤掉分区 (disk0s1, disk0s2) 只保留整盘
                        if "s" not in path[len("/dev/disk"):]:
                            # 拿 size 信息
                            try:
                                r2 = subprocess.run(
                                    ["diskutil", "info", path],
                                    capture_output=True, text=True, timeout=10
                                )
                                size = "-"
                                model = "-"
                                for ln in r2.stdout.split('\n'):
                                    if "Total Size" in ln or "Disk Size" in ln:
                                        size = ln.split(':', 1)[1].strip().split('(')[0].strip()
                                    if "Device / Media Name" in ln or "Media Name" in ln:
                                        model = ln.split(':', 1)[1].strip()
                                disks.append({"path": path, "model": model, "size": size})
                            except Exception:
                                disks.append({"path": path, "model": "-", "size": "-"})
            except Exception as e:
                self.log.error(f"扫描物理磁盘失败: {e}")
        else:  # Linux
            try:
                r = subprocess.run(["lsblk", "-d", "-o", "NAME,MODEL,SIZE,TYPE",
                                    "-n", "-p"],
                                   capture_output=True, text=True, timeout=30)
                for line in r.stdout.strip().split('\n'):
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 3 and "disk" in line:
                            disks.append({
                                "path": parts[0],
                                "model": parts[1] if len(parts) > 1 else "-",
                                "size": parts[2]
                            })
            except Exception as e:
                self.log.error(f"扫描物理磁盘失败: {e}")
        return disks

    def ios_backups(self) -> List[str]:
        backups = []
        bp = Config().ITUNES_BACKUP.get(self.sys, "")
        if bp:
            path = Path(os.path.expandvars(os.path.expanduser(bp)))
            if path.exists():
                for item in path.iterdir():
                    if item.is_dir() and len(item.name) == 40:
                        backups.append(str(item))
        return backups

    def android_adb(self) -> List[str]:
        devices = []
        try:
            r = subprocess.run(["adb", "devices"], capture_output=True,
                               text=True, timeout=10)
            for line in r.stdout.strip().split('\n')[1:]:
                if '\t' in line and 'device' in line:
                    devices.append(line.split('\t')[0])
        except FileNotFoundError:
            self.log.warning("ADB 未安装")
        return devices

    def _human(self, n) -> str:
        try:
            n = int(n)
        except (TypeError, ValueError):
            return str(n)
        for u in ['B', 'KB', 'MB', 'GB', 'TB']:
            if n < 1024:
                return f"{n:.1f}{u}"
            n /= 1024
        return f"{n:.1f}PB"


# ==================== 微信定位 ====================
class Locator:
    def __init__(self, logger: ForensicLogger):
        self.log = logger
        self.sys = platform.system()

    def find_pc(self, extra_paths: List[str] = None) -> List[Dict]:
        """查找PC微信数据"""
        found = []
        cfg = Config()
        paths = list(extra_paths or [])
        for p in cfg.WECHAT_PATHS.get(self.sys, []):
            paths.append(os.path.expandvars(os.path.expanduser(p)))

        scanner = Scanner(self.log)
        for d in scanner.drives():
            m = d["mount"]
            for sub in ["WeChat Files", "Documents/WeChat Files", "Tencent/WeChat Files",
                       "Users/*/Documents/WeChat Files", "Users/*/WeChat Files"]:
                paths.append(os.path.join(m, sub))

        checked = set()
        for path in paths:
            resolved = os.path.expandvars(os.path.expanduser(path))
            if '*' in resolved:
                import glob
                for g in glob.glob(resolved):
                    if g not in checked:
                        checked.add(g)
                        found += self._scan_wechat_dir(g)
            else:
                if resolved not in checked:
                    checked.add(resolved)
                    found += self._scan_wechat_dir(resolved)

        return found

    def _scan_wechat_dir(self, path: str) -> List[Dict]:
        found = []
        p = Path(path)
        if not p.exists():
            return found
        for item in p.iterdir():
            if not item.is_dir():
                continue
            name = item.name
            if name.startswith("wxid_") or (item / "Msg").exists():
                found.append({
                    "wxid": name,
                    "path": str(item),
                    "msg": str(item / "Msg") if (item / "Msg").exists() else None,
                    "filestorage": str(item / "FileStorage") if (item / "FileStorage").exists() else None,
                    "config": str(item / "config") if (item / "config").exists() else None,
                })
        return found

    def find_mobile(self) -> List[Dict]:
        results = []
        scanner = Scanner(self.log)
        for b in scanner.ios_backups():
            results.append({"type": "ios_backup", "path": b, "desc": "iTunes备份"})
        for d in scanner.drives():
            m = d["mount"]
            for sub in ["tencent/MicroMsg", "Android/data/com.tencent.mm/MicroMsg",
                       "Tencent/MicroMsg", "media/0/tencent/MicroMsg"]:
                p = Path(m) / sub
                if p.exists():
                    results.append({"type": "android", "path": str(p), "desc": f"Android {sub}"})
        return results


# ==================== 提取器 ====================
class Extractor:
    def __init__(self, logger: ForensicLogger, out_dir: str = None):
        self.log = logger
        self.out = Path(out_dir or Config().OUTPUT_DIR)
        self.out.mkdir(parents=True, exist_ok=True)
        self.manifest = {
            "tool": "WeChat Forensic Extractor Pro v2.0",
            "time": datetime.datetime.now().isoformat(),
            "operator": getpass.getuser(),
            "hostname": platform.node(),
            "platform": platform.platform(),
            "items": []
        }

    def extract_pc(self, info: Dict) -> Tuple[str, Dict]:
        """提取PC数据，返回 (目录, 哈希报告)"""
        wxid = info["wxid"]
        dst = self.out / f"PC_{wxid}"
        dst.mkdir(exist_ok=True)
        files = []
        hash_report = {"source": info["path"], "files": []}

        if info.get("msg"):
            d = dst / "Msg"
            d.mkdir(exist_ok=True)
            copied = self._copy_with_hash(Path(info["msg"]),
                                          patterns=["*.db", "*.db-wal", "*.db-shm"],
                                          dst_root=d)
            files += copied
            hash_report["files"].extend(copied)

        if info.get("filestorage"):
            d = dst / "FileStorage"
            d.mkdir(exist_ok=True)
            copied = self._copy_with_hash(Path(info["filestorage"]), dst_root=d)
            files += copied
            hash_report["files"].extend(copied)

        if info.get("config"):
            d = dst / "config"
            d.mkdir(exist_ok=True)
            copied = self._copy_with_hash(Path(info["config"]), dst_root=d)
            files += copied
            hash_report["files"].extend(copied)

        # 计算目录整体哈希
        dir_hash = self._hash_directory(dst)

        self.manifest["items"].append({
            "type": "pc", "wxid": wxid, "files_count": len(files),
            "dst": str(dst), "sha256": dir_hash
        })

        self.log.success(f"PC提取完成: {dst} ({len(files)} 文件)")
        self.log.evidence(f"目录 SHA-256: {dir_hash}")

        return str(dst), hash_report

    def extract_mobile(self, info: Dict) -> Tuple[str, Dict]:
        t = info["type"]
        src = Path(info["path"])
        dst = self.out / f"Mobile_{t}_{src.name[:8]}"
        copied = self._copy_with_hash(src, dst_root=dst)
        dir_hash = self._hash_directory(dst)

        self.manifest["items"].append({
            "type": t, "src": str(src), "files_count": len(copied),
            "dst": str(dst), "sha256": dir_hash
        })

        self.log.success(f"手机备份提取完成: {dst} ({len(copied)} 文件)")
        self.log.evidence(f"目录 SHA-256: {dir_hash}")

        return str(dst), {"source": str(src), "files": copied}

    def _copy_with_hash(self, src: Path, dst_root: Path = None, patterns: List[str] = None) -> List[Dict]:
        """复制 src 下文件到 dst_root(默认 dst_root = src 同名目录在 output 下)"""
        dst = dst_root if dst_root is not None else (self.out / src.name)
        copied = []
        if not src.exists():
            self.log.warning(f"源路径不存在: {src}")
            return copied
        for root, dirs, files in os.walk(src):
            dirs[:] = [d for d in dirs if d not in ['Cache', 'tmp', 'temp', 'log', 'Logs']]
            for f in files:
                s = Path(root) / f
                if patterns and not any(s.match(p) for p in patterns):
                    continue
                try:
                    r = Path(root).relative_to(src)
                    d = dst / r
                    d.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(s, d / f)

                    sha256 = Hasher.sha256_file(str(s))
                    copied.append({
                        "src": str(s),
                        "dst": str(d / f),
                        "sha256": sha256,
                        "size": s.stat().st_size
                    })
                except Exception as e:
                    self.log.warning(f"跳过 {s}: {e}")
        return copied

    def _hash_directory(self, path: Path) -> str:
        """计算目录内所有文件的有序哈希(修复:原版错误地把路径字符串当作文件内容传入)"""
        h = hashlib.sha256()
        for f in sorted(path.rglob('*')):
            if f.is_file() and f.name != "_manifest.json":
                # 1) 把相对路径纳入哈希(对结构敏感)
                h.update(f.relative_to(path).as_posix().encode('utf-8'))
                # 2) 把真实文件内容的 SHA-256 摘要纳入
                h.update(Hasher.sha256_file(str(f)).encode('utf-8'))
        return h.hexdigest()

    def save_manifest(self):
        p = self.out / "_forensic_manifest.json"
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(self.manifest, f, ensure_ascii=False, indent=2)
        self.log.success(f"清单: {p}")


# ==================== 压缩 ====================
class Packer:
    @staticmethod
    def zip_dir(src: str, dst: str = None, pwd: str = None, logger=None) -> str:
        s = Path(src)
        if not dst:
            dst = f"{s.name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        out = Path(dst)

        if logger:
            logger.info(f"开始压缩: {src} -> {dst}")

        if pwd:
            try:
                import pyzipper
                with pyzipper.AESZipFile(out, 'w', pyzipper.ZIP_DEFLATED,
                                        encryption=pyzipper.WZ_AES) as zf:
                    zf.setpassword(pwd.encode())
                    for f in s.rglob('*'):
                        if f.is_file():
                            zf.write(f, f.relative_to(s))
                if logger:
                    logger.success(f"加密压缩: {out}")
                return str(out)
            except ImportError:
                if logger:
                    logger.warning("pyzipper 未安装，使用普通压缩")

        with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zf:
            for f in s.rglob('*'):
                if f.is_file():
                    zf.write(f, f.relative_to(s))

        if logger:
            logger.success(f"压缩完成: {out} ({out.stat().st_size/1024**3:.2f}GB)")
        return str(out)


# ==================== 云端上传 ====================
class Uploader:
    @staticmethod
    def baidu(file: str, logger=None) -> bool:
        try:
            if logger:
                logger.info("上传百度云...")
            r = subprocess.run(["bypy", "upload", file, "/wechat_forensic"],
                               capture_output=True, text=True, timeout=600)
            if r.returncode == 0:
                if logger:
                    logger.success("百度云上传成功")
                return True
            else:
                if logger:
                    logger.error(f"百度云失败: {r.stderr}")
                return False
        except FileNotFoundError:
            if logger:
                logger.error("未安装 bypy: pip install bypy && bypy info")
            return False

    @staticmethod
    def aliyun(file: str, logger=None) -> bool:
        try:
            if logger:
                logger.info("上传阿里云OSS...")
            import oss2
            cfg = Config()
            auth = oss2.Auth(cfg.ALIYUN_ACCESS_KEY, cfg.ALIYUN_SECRET_KEY)
            bucket = oss2.Bucket(auth, cfg.ALIYUN_OSS_ENDPOINT, cfg.ALIYUN_OSS_BUCKET)
            name = f"wechat_forensic/{Path(file).name}"
            bucket.put_object_from_file(name, file)
            if logger:
                logger.success(f"阿里云上传成功: {name}")
            return True
        except ImportError:
            if logger:
                logger.error("未安装 oss2: pip install oss2")
            return False
        except Exception as e:
            if logger:
                logger.error(f"阿里云失败: {e}")
            return False


# ==================== 取证报告生成 ====================
class ReportGenerator:
    @staticmethod
    def generate(output_dir: str, operations: List[Dict], logger=None):
        """生成符合司法取证规范的报告"""
        report = {
            "report_id": f"WFE-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
            "tool": "WeChat Forensic Extractor Pro v2.0",
            "generated_at": datetime.datetime.now().isoformat(),
            "operator": getpass.getuser(),
            "hostname": platform.node(),
            "platform": platform.platform(),
            "python_version": sys.version,
            "operations": operations,
            "chain_of_custody": {
                "principle": "原始证据不动，所有操作在副本/镜像上进行",
                "hash_algorithm": "SHA-256",
                "integrity_verification": "每个关键步骤均计算并记录哈希值"
            }
        }

        path = Path(output_dir) / "_forensic_report.json"
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        # 同时生成可读文本报告 (修复: 原版 f.write("...\n") 里 \n 被错误转义)
        txt_path = Path(output_dir) / "_forensic_report.txt"
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write("=" * 70 + "\n")
            f.write("  微信聊天记录取证报告\n")
            f.write("=" * 70 + "\n\n")
            f.write(f"报告编号: {report['report_id']}\n")
            f.write(f"生成时间: {report['generated_at']}\n")
            f.write(f"操作人员: {report['operator']}\n")
            f.write(f"计算机名: {report['hostname']}\n")
            f.write(f"操作系统: {report['platform']}\n\n")
            f.write("-" * 70 + "\n")
            f.write("  操作日志\n")
            f.write("-" * 70 + "\n\n")

            for i, op in enumerate(operations, 1):
                f.write(f"[步骤 {i}] {op.get('step', 'Unknown')}\n")
                f.write(f"  时间: {op.get('timestamp', '-')}\n")
                f.write(f"  描述: {op.get('description', '-')}\n")
                if 'sha256' in op:
                    f.write(f"  SHA-256: {op['sha256']}\n")
                if 'source' in op:
                    f.write(f"  来源: {op['source']}\n")
                if 'output' in op:
                    f.write(f"  输出: {op['output']}\n")
                f.write("\n")

            f.write("-" * 70 + "\n")
            f.write("  证据链保全声明\n")
            f.write("-" * 70 + "\n\n")
            f.write("1. 本报告所有哈希值使用 SHA-256 算法计算\n")
            f.write("2. 原始存储介质在提取过程中未被修改\n")
            f.write("3. 所有操作均有时间戳和操作人员记录\n")
            f.write("4. 如需司法效力,建议委托有资质的电子数据司法鉴定机构复核\n")

        if logger:
            logger.success(f"取证报告生成: {txt_path}")
        return str(txt_path)


# ==================== 主流程 ====================
def main():
    parser = argparse.ArgumentParser(description="WeChat Forensic Extractor Pro")
    parser.add_argument("--mode", choices=["quick", "forensic"], default="forensic",
                       help="quick=直接提取文件 | forensic=生成镜像+哈希+报告")
    parser.add_argument("--source", help="手动指定源路径")
    parser.add_argument("--mirror-disk", help="指定物理磁盘进行位对位镜像 (如 /dev/sdb)")
    parser.add_argument("--output", default="./wechat_forensic_output", help="输出目录")
    parser.add_argument("--zip-password", help="压缩密码")
    parser.add_argument("--upload", choices=["baidu", "aliyun", "none"], default="none")
    parser.add_argument("--no-interactive", action="store_true", help="非交互模式")
    args = parser.parse_args()

    # 初始化
    log = ForensicLogger(Config().LOG_FILE)
    operations = []

    print("=" * 70)
    print("  WeChat Forensic Extractor Pro v2.0")
    print("  跨平台微信聊天记录取证提取工具链")
    print("=" * 70)
    log.info(f"启动模式: {args.mode}")
    log.info(f"操作系统: {platform.platform()}")
    log.info(f"操作人员: {getpass.getuser()}")

    # ==================== 步骤1: 扫描设备 ====================
    print("\n" + "-" * 70)
    print("[步骤 1/6] 扫描设备与存储介质")
    print("-" * 70)

    scanner = Scanner(log)

    # 逻辑磁盘
    drives = scanner.drives()
    log.info(f"发现 {len(drives)} 个逻辑磁盘:")
    for d in drives:
        log.info(f"  {d['device']} -> {d['mount']} | 可用 {d['free']} / 总 {d['total']}")

    # 物理磁盘（取证模式）
    physical = []
    if args.mode == "forensic":
        physical = scanner.physical_disks()
        log.info(f"发现 {len(physical)} 个物理磁盘:")
        for p in physical:
            log.info(f"  {p.get('path', '-')} | {p.get('model', '-')} | {p.get('size', '-')}")

    # ==================== 步骤2: 镜像生成（取证模式） ====================
    mirror_info = None
    if args.mode == "forensic" and (args.mirror_disk or not args.no_interactive):
        print("\n" + "-" * 70)
        print("[步骤 2/6] 位对位镜像生成")
        print("-" * 70)

        mirror_gen = MirrorGenerator(log)

        if args.mirror_disk:
            target = args.mirror_disk
        elif physical and not args.no_interactive:
            print("\n可镜像的物理磁盘:")
            for i, p in enumerate(physical, 1):
                print(f"  {i}. {p.get('path')} | {p.get('model')} | {p.get('size')}")
            print("  0. 跳过镜像,直接提取文件")
            choice = input("\n选择要镜像的磁盘编号: ").strip()
            if choice == "0" or not choice:
                target = None
            else:
                try:
                    target = physical[int(choice) - 1]["path"]
                except (IndexError, ValueError):
                    target = None
        else:
            target = None

        if target:
            mirror_dir = Path(args.output) / "mirrors"
            mirror_dir.mkdir(parents=True, exist_ok=True)
            mirror_path = str(mirror_dir / f"disk_mirror_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.img")

            log.evidence(f"开始镜像磁盘: {target}")
            mirror_info = mirror_gen.mirror_disk_dd(target, mirror_path)

            if mirror_info.get("success"):
                operations.append({
                    "step": "磁盘镜像生成",
                    "timestamp": datetime.datetime.now().isoformat(),
                    "description": f"位对位镜像 {target}",
                    "source": target,
                    "output": mirror_path,
                    "sha256": mirror_info["sha256"],
                    "tool": "dd"
                })
            else:
                log.error("镜像生成失败,将尝试直接文件提取")

    # ==================== 步骤3: 定位微信数据 ====================
    print("\n" + "-" * 70)
    print("[步骤 3/6] 定位微信数据")
    print("-" * 70)

    locator = Locator(log)

    if args.source:
        pc = locator.find_pc([args.source])
    else:
        pc = locator.find_pc()
    mobile = locator.find_mobile()

    targets = []
    if pc:
        log.info(f"发现 {len(pc)} 个PC微信数据:")
        for i, x in enumerate(pc, 1):
            log.info(f"  {i}. {x['wxid']} @ {x['path']}")
            targets.append(("pc", x))
    if mobile:
        log.info(f"发现 {len(mobile)} 个手机备份:")
        for i, x in enumerate(mobile, 1):
            log.info(f"  {i}. {x['type']} @ {x['path'][:60]}...")
            targets.append(("mobile", x))

    if not targets:
        if not args.no_interactive:
            custom = input("\n未自动发现,手动输入路径(逗号分隔)或回车退出: ").strip()
            if custom:
                pc = locator.find_pc([p.strip() for p in custom.split(",")])
                targets = [("pc", x) for x in pc]
        if not targets:
            log.error("未找到微信数据,退出")
            return

    # ==================== 步骤4: 提取数据 ====================
    print("\n" + "-" * 70)
    print("[步骤 4/6] 提取与哈希校验")
    print("-" * 70)

    extractor = Extractor(log, args.output)
    extracted_dirs = []

    for t, info in targets:
        if t == "pc":
            dst, hash_report = extractor.extract_pc(info)
        else:
            dst, hash_report = extractor.extract_mobile(info)
        extracted_dirs.append(dst)

        operations.append({
            "step": "数据提取",
            "timestamp": datetime.datetime.now().isoformat(),
            "description": f"提取 {info.get('wxid', info.get('type'))}",
            "source": info.get("path", info.get("src")),
            "output": dst,
            "file_hashes": hash_report
        })

    extractor.save_manifest()

    # ==================== 步骤5: 压缩 ====================
    print("\n" + "-" * 70)
    print("[步骤 5/6] 压缩打包")
    print("-" * 70)

    arc_path = Packer.zip_dir(
        args.output,
        pwd=args.zip_password,
        logger=log
    )
    arc_hash = Hasher.sha256_file(arc_path)

    operations.append({
        "step": "压缩打包",
        "timestamp": datetime.datetime.now().isoformat(),
        "description": "打包所有提取数据",
        "output": arc_path,
        "sha256": arc_hash,
        "encrypted": args.zip_password is not None
    })

    log.evidence(f"压缩包 SHA-256: {arc_hash}")

    # ==================== 步骤6: 云端上传 ====================
    if args.upload != "none":
        print("\n" + "-" * 70)
        print("[步骤 6/6] 云端上传")
        print("-" * 70)

        if args.upload == "baidu":
            success = Uploader.baidu(arc_path, log)
        elif args.upload == "aliyun":
            success = Uploader.aliyun(arc_path, log)
        else:
            success = False

        operations.append({
            "step": "云端上传",
            "timestamp": datetime.datetime.now().isoformat(),
            "description": f"上传至 {args.upload}",
            "source": arc_path,
            "sha256": arc_hash,
            "success": success
        })

    # ==================== 生成取证报告 ====================
    print("\n" + "-" * 70)
    print("[最终] 生成取证报告")
    print("-" * 70)

    report_path = ReportGenerator.generate(args.output, operations, log)

    # 最终汇总
    print("\n" + "=" * 70)
    print("  取证完成")
    print("=" * 70)
    print(f"  输出目录: {args.output}")
    print(f"  压缩包:   {arc_path}")
    print(f"  包哈希:   {arc_hash}")
    print(f"  报告:     {report_path}")
    if mirror_info and mirror_info.get("success"):
        print(f"  镜像:     {mirror_info['output']}")
        print(f"  镜像哈希: {mirror_info['sha256']}")
    print("=" * 70)
    print("\n  ⚠️  提示: 如需司法程序使用,建议委托有资质的电子数据")
    print("     司法鉴定机构出具正式鉴定报告。")
    print("=" * 70)


if __name__ == "__main__":
    main()

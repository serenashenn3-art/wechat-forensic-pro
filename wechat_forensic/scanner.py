"""设备与存储介质扫描"""

import csv
import os
import platform
import re
import subprocess
from pathlib import Path
from typing import List

from .utils import human_bytes


class Scanner:
    def __init__(self, logger):
        self.log = logger
        self.sys = platform.system()

    # ---------- 逻辑磁盘 ----------
    def drives(self) -> List[dict]:
        drives: List[dict] = []
        if self.sys == "Windows":
            # Windows 优先使用 WMI/PowerShell,保证字段格式与测试一致
            drives = self._scan_windows_drives()
        else:
            try:
                import psutil  # type: ignore

                for p in psutil.disk_partitions(all=True):
                    try:
                        u = psutil.disk_usage(p.mountpoint)
                        drives.append(
                            {
                                "device": p.device,
                                "mount": p.mountpoint,
                                "fstype": p.fstype,
                                "opts": p.opts,
                                "free": human_bytes(u.free),
                                "used": human_bytes(u.used),
                                "total": human_bytes(u.total),
                                "free_bytes": u.free,
                            }
                        )
                    except (PermissionError, OSError):
                        continue
            except ImportError:
                self.log.warning("未安装 psutil,使用系统命令扫描")
                drives = self._fallback_scan()
        return drives

    def _fallback_scan(self) -> List[dict]:
        drives: List[dict] = []
        if self.sys == "Windows":
            drives = self._scan_windows_drives()
        else:
            drives = self._scan_unix_drives()
        return drives

    def _scan_windows_drives(self) -> List[dict]:
        drives: List[dict] = []
        ps_cmd = (
            "Get-CimInstance Win32_LogicalDisk | "
            "Select-Object DeviceID,Size,FreeSpace,FileSystem,VolumeName | "
            "ConvertTo-Csv -NoTypeInformation"
        )
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if r.returncode == 0 and r.stdout.strip():
                reader = csv.DictReader(r.stdout.strip().split("\n"))
                for row in reader:
                    device = row.get("DeviceID", "").strip().strip('"')
                    if not device:
                        continue
                    size = int(row["Size"]) if row.get("Size", "").strip().isdigit() else 0
                    free = int(row["FreeSpace"]) if row.get("FreeSpace", "").strip().isdigit() else 0
                    drives.append(
                        {
                            "device": device,
                            "mount": device,
                            "fstype": row.get("FileSystem", "").strip().strip('"') or "-",
                            "label": row.get("VolumeName", "").strip().strip('"') or "-",
                            "free": human_bytes(free),
                            "used": human_bytes(size - free),
                            "total": human_bytes(size),
                            "free_bytes": free,
                        }
                    )
                return drives
        except FileNotFoundError:
            self.log.warning("未找到 powershell,尝试 wmic")
        except Exception as e:
            self.log.error(f"PowerShell 扫描失败: {e}")

        # 回退: wmic
        try:
            r = subprocess.run(
                ["wmic", "logicaldisk", "get", "DeviceID,Size,FreeSpace,FileSystem,VolumeName"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            for line in r.stdout.strip().split("\n")[1:]:
                parts = line.split()
                if len(parts) >= 4:
                    drives.append(
                        {
                            "device": parts[0],
                            "mount": parts[0],
                            "fstype": parts[3] if len(parts) > 3 else "-",
                            "label": parts[4] if len(parts) > 4 else "-",
                            "free": "-",
                            "total": "-",
                            "free_bytes": 0,
                        }
                    )
        except Exception as e:
            self.log.error(f"wmic 扫描失败: {e}")
        return drives

    def _scan_unix_drives(self) -> List[dict]:
        drives: List[dict] = []
        try:
            r = subprocess.run(["df", "-h"], capture_output=True, text=True, timeout=30)
            for line in r.stdout.strip().split("\n")[1:]:
                p = line.split()
                if len(p) >= 6:
                    drives.append(
                        {
                            "device": p[0],
                            "mount": p[5],
                            "fstype": "-",
                            "free": p[3],
                            "total": p[1],
                            "free_bytes": 0,
                        }
                    )
        except Exception as e:
            self.log.error(f"df 扫描失败: {e}")
        return drives

    # ---------- 物理磁盘 ----------
    def physical_disks(self) -> List[dict]:
        disks: List[dict] = []
        if self.sys == "Windows":
            return self._scan_physical_windows()
        if self.sys == "Darwin":
            return self._scan_physical_darwin()
        return self._scan_physical_linux()

    def _scan_physical_windows(self) -> List[dict]:
        disks: List[dict] = []
        ps_cmd = (
            "Get-CimInstance Win32_DiskDrive | "
            "Select-Object Index,Model,Size,MediaType,InterfaceType | "
            "ConvertTo-Csv -NoTypeInformation"
        )
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if r.returncode == 0 and r.stdout.strip():
                for line in r.stdout.strip().split("\n")[1:]:
                    parts = [p.strip().strip('"') for p in line.split(",")]
                    if len(parts) >= 3 and parts[0]:
                        size_bytes = int(parts[2]) if parts[2].isdigit() else 0
                        disks.append(
                            {
                                "index": parts[0],
                                "model": parts[1] if len(parts) > 1 else "-",
                                "size": human_bytes(size_bytes),
                                "size_bytes": size_bytes,
                                "media": parts[3] if len(parts) > 3 else "-",
                                "interface": parts[4] if len(parts) > 4 else "-",
                                "path": f"\\\\.\\PhysicalDrive{parts[0]}",
                            }
                        )
                return disks
        except FileNotFoundError:
            self.log.warning("未找到 powershell,尝试 wmic")
        except Exception as e:
            self.log.error(f"PowerShell 物理磁盘扫描失败: {e}")

        try:
            r = subprocess.run(
                ["wmic", "diskdrive", "get", "Index,Model,Size,MediaType,InterfaceType", "/format:csv"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            for line in r.stdout.strip().split("\n")[1:]:
                if line.strip():
                    parts = line.split(",")
                    if len(parts) >= 5:
                        disks.append(
                            {
                                "index": parts[1],
                                "model": parts[2],
                                "size": parts[3],
                                "media": parts[4],
                                "path": f"\\\\.\\PhysicalDrive{parts[1]}",
                            }
                        )
        except Exception as e:
            self.log.error(f"wmic 物理磁盘扫描失败: {e}")
        return disks

    def _scan_physical_darwin(self) -> List[dict]:
        disks: List[dict] = []
        try:
            r = subprocess.run(["diskutil", "list"], capture_output=True, text=True, timeout=30)
            for line in r.stdout.split("\n"):
                line = line.strip()
                if line.startswith("/dev/disk") and ":" in line:
                    path = line.split()[0]
                    # 过滤分区 disk0s1/disk0s2, 只保留整盘 disk0
                    if not re.fullmatch(r"/dev/disk\d+", path):
                        continue
                    try:
                        r2 = subprocess.run(
                            ["diskutil", "info", path],
                            capture_output=True,
                            text=True,
                            timeout=10,
                        )
                        size, model = "-", "-"
                        for ln in r2.stdout.split("\n"):
                            if "Total Size" in ln or "Disk Size" in ln:
                                size = ln.split(":", 1)[1].strip().split("(")[0].strip()
                            if "Device / Media Name" in ln or "Media Name" in ln:
                                model = ln.split(":", 1)[1].strip()
                        disks.append({"path": path, "model": model, "size": size})
                    except Exception:
                        disks.append({"path": path, "model": "-", "size": "-"})
        except Exception as e:
            self.log.error(f"macOS 物理磁盘扫描失败: {e}")
        return disks

    def _scan_physical_linux(self) -> List[dict]:
        disks: List[dict] = []
        try:
            r = subprocess.run(
                ["lsblk", "-d", "-o", "NAME,MODEL,SIZE,TYPE", "-n", "-p"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            for line in r.stdout.strip().split("\n"):
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 3 and "disk" in line:
                        disks.append(
                            {
                                "path": parts[0],
                                "model": parts[1] if len(parts) > 1 else "-",
                                "size": parts[2],
                            }
                        )
        except Exception as e:
            self.log.error(f"lsblk 扫描失败: {e}")
        return disks

    # ---------- 移动端 ----------
    def ios_backups(self) -> List[str]:
        from .config import Config

        backups: List[str] = []
        bp = Config().ITUNES_BACKUP.get(self.sys, "")
        if bp:
            path = Path(os.path.expandvars(os.path.expanduser(bp)))
            if path.exists():
                for item in path.iterdir():
                    # UDID 为 40 位(旧设备)或 64 位(新设备)十六进制字符串
                    if item.is_dir() and len(item.name) in (40, 64):
                        try:
                            int(item.name, 16)
                            backups.append(str(item))
                        except ValueError:
                            continue
        return backups

    def android_adb(self) -> List[str]:
        devices: List[str] = []
        try:
            r = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=10)
            for line in r.stdout.strip().split("\n")[1:]:
                if "\t" in line and "device" in line:
                    devices.append(line.split("\t")[0])
        except FileNotFoundError:
            self.log.warning("ADB 未安装")
        return devices

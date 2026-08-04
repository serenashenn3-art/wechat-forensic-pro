"""微信数据定位"""

import glob
import os
import platform
from pathlib import Path
from typing import Dict, List


class Locator:
    def __init__(self, logger):
        self.log = logger
        self.sys = platform.system()

    def find_pc(self, extra_paths: List[str] = None) -> List[Dict]:
        """查找 PC 微信数据"""
        from .config import Config
        from .scanner import Scanner

        found: List[Dict] = []
        cfg = Config()
        paths = list(extra_paths or [])
        for p in cfg.WECHAT_PATHS.get(self.sys, []):
            paths.append(os.path.expandvars(os.path.expanduser(p)))

        scanner = Scanner(self.log)
        for d in scanner.drives():
            m = d["mount"]
            for sub in [
                "WeChat Files",
                "Documents/WeChat Files",
                "Tencent/WeChat Files",
                "Users/*/Documents/WeChat Files",
                "Users/*/WeChat Files",
            ]:
                paths.append(os.path.join(m, sub))

        checked = set()
        for path in paths:
            resolved = os.path.expandvars(os.path.expanduser(path))
            if "*" in resolved:
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
        found: List[Dict] = []
        p = Path(path)
        if not p.exists():
            return found
        for item in p.iterdir():
            if not item.is_dir():
                continue
            if item.name.startswith("wxid_") or (item / "Msg").exists():
                found.append(
                    {
                        "wxid": item.name,
                        "path": str(item),
                        "msg": str(item / "Msg") if (item / "Msg").exists() else None,
                        "filestorage": str(item / "FileStorage") if (item / "FileStorage").exists() else None,
                        "config": str(item / "config") if (item / "config").exists() else None,
                    }
                )
            # macOS 原生微信沙盒结构: 2.0b4.0.9/Avatar/KeyValue/MMappedKV/...
            elif self._is_macos_wechat_version_dir(item):
                found.append(
                    {
                        "wxid": f"macos_{item.name}",
                        "path": str(item),
                        "msg": None,
                        "filestorage": str(item),
                        "config": None,
                        "note": "macOS WeChat sandbox version directory",
                    }
                )
        return found

    @staticmethod
    def _is_macos_wechat_version_dir(item: Path) -> bool:
        """判断是否为 macOS 原生微信沙盒中的版本目录

        特征: 目录名类似 2.0b4.0.9, 且包含 macOS 微信特有子目录
        """
        name = item.name
        # 版本号格式: x.xbx.x 或 x.x.x.x
        if not (name[0].isdigit() and ("." in name)):
            return False
        # macOS 微信沙盒目录典型子目录
        macos_markers = {"Avatar", "KeyValue", "MMappedKV", "MMResourceMgr", "CGI", "nsid"}
        try:
            children = {c.name for c in item.iterdir() if c.is_dir()}
        except PermissionError:
            return False
        return bool(children & macos_markers)

    def find_mobile(self) -> List[Dict]:
        from pathlib import Path

        from .config import Config
        from .scanner import Scanner

        cfg = Config()
        results: List[Dict] = []
        scanner = Scanner(self.log)

        # iOS 备份: 目录名是 UDID 去掉横线的小写 hex (40 或 64 位)
        for b in scanner.ios_backups():
            results.append(
                {
                    "type": "ios_backup",
                    "path": b,
                    "udid": Path(b).name,
                    "desc": "iTunes 备份",
                }
            )

        # Android: 扫描 Config.ANDROID_DATA_PATHS,区分 Scoped Storage / 旧版 / /data/data
        for d in scanner.drives():
            m = d["mount"]
            for sub in cfg.ANDROID_DATA_PATHS:
                p = Path(sub if sub.startswith("/") else str(Path(m) / sub.lstrip("/")))
                if p.exists():
                    if "/Android/data/" in str(p) or "/data/data/" in str(p):
                        privilege = "需要 root 或 ADB 授权 (Scoped Storage 限制)"
                    else:
                        privilege = "可直接读取 (Android 10 及以下)"
                    results.append(
                        {
                            "type": "android",
                            "path": str(p),
                            "desc": f"Android {sub}",
                            "privilege": privilege,
                        }
                    )
        return results

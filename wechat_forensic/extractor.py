"""数据提取器"""

import datetime
import getpass
import hashlib
import json
import os
import platform
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

from .hashing import Hasher
from . import __version__


class Extractor:
    def __init__(self, logger, out_dir: str = None):
        self.log = logger
        self.out = Path(out_dir or "./wechat_forensic_output")
        self.out.mkdir(parents=True, exist_ok=True)
        self.manifest = {
            "tool": f"WeChat Forensic Extractor Pro {__version__}",
            "time": datetime.datetime.now().isoformat(),
            "operator": getpass.getuser(),
            "hostname": platform.node(),
            "platform": platform.platform(),
            "items": [],
        }

    def extract_pc(self, info: Dict) -> Tuple[str, Dict]:
        """提取 PC 数据"""
        self.log.info(f"WeChat Forensic Extractor Pro {__version__} - PC Extraction")
        wxid = info["wxid"]
        dst = self.out / f"PC_{wxid}"
        dst.mkdir(exist_ok=True)
        files: List[Dict] = []
        hash_report = {"source": info["path"], "files": []}

        if info.get("msg"):
            d = dst / "Msg"
            d.mkdir(exist_ok=True)
            copied = self._copy_with_hash(
                Path(info["msg"]),
                dst_root=d,
                patterns=["*.db", "*.db-wal", "*.db-shm"],
            )
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

        dir_hash = self._hash_directory(dst)
        self.manifest["items"].append(
            {
                "type": "pc",
                "wxid": wxid,
                "files_count": len(files),
                "dst": str(dst),
                "sha256": dir_hash,
            }
        )
        self.log.success(f"PC 提取完成: {dst} ({len(files)} 文件)")
        self.log.evidence(f"目录 SHA-256: {dir_hash}")
        return str(dst), hash_report

    def extract_mobile(self, info: Dict) -> Tuple[str, Dict]:
        t = info["type"]
        src = Path(info["path"])
        dst = self.out / f"Mobile_{t}_{src.name[:8]}"
        copied = self._copy_with_hash(src, dst_root=dst)
        dir_hash = self._hash_directory(dst)
        self.manifest["items"].append(
            {
                "type": t,
                "src": str(src),
                "files_count": len(copied),
                "dst": str(dst),
                "sha256": dir_hash,
            }
        )
        self.log.success(f"手机备份提取完成: {dst} ({len(copied)} 文件)")
        self.log.evidence(f"目录 SHA-256: {dir_hash}")
        return str(dst), {"source": str(src), "files": copied}

    def _copy_with_hash(
        self,
        src: Path,
        dst_root: Path = None,
        patterns: List[str] = None,
    ) -> List[Dict]:
        """复制 src 下文件到 dst_root,逐文件计算 SHA-256"""
        dst = dst_root if dst_root is not None else (self.out / src.name)
        copied: List[Dict] = []
        if not src.exists():
            self.log.warning(f"源路径不存在: {src}")
            return copied
        for root, dirs, files in os.walk(src):
            dirs[:] = [d for d in dirs if d not in ["Cache", "tmp", "temp", "log", "Logs"]]
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
                    copied.append(
                        {
                            "src": str(s),
                            "dst": str(d / f),
                            "sha256": sha256,
                            "size": s.stat().st_size,
                        }
                    )
                except Exception as e:
                    self.log.warning(f"跳过 {s}: {e}")
        return copied

    def _hash_directory(self, path: Path) -> str:
        """目录内所有文件的有序哈希(相对路径 + 文件内容 SHA-256)"""
        h = hashlib.sha256()
        files = []
        for f in sorted(path.rglob("*")):
            if f.is_file() and f.name != "_forensic_manifest.json":
                # rglob 出来的 f 本身没有"根目录之外"的相对路径概念,
                # 必须用 f.relative_to(path) 才能拿到完整子路径
                files.append((f.relative_to(path).as_posix(), f))
        for rel, f in files:
            h.update(rel.encode("utf-8"))
            h.update(Hasher.sha256_file(str(f)).encode("utf-8"))
        return h.hexdigest()

    def save_manifest(self):
        p = self.out / "_forensic_manifest.json"
        with open(p, "w", encoding="utf-8") as f:
            json.dump(self.manifest, f, ensure_ascii=False, indent=2)
        self.log.success(f"清单: {p}")

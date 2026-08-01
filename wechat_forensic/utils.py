"""跨平台工具函数"""

import os
import sys


def is_admin() -> bool:
    """判断当前进程是否具有管理员/root 权限(跨平台)"""
    try:
        if os.name == "nt":
            try:
                import ctypes  # type: ignore

                return bool(ctypes.windll.shell32.IsUserAnAdmin())
            except Exception:
                return False
        return os.geteuid() == 0
    except Exception:
        return False


def human_bytes(n) -> str:
    """字节数 -> 可读字符串"""
    try:
        n = int(n)
    except (TypeError, ValueError):
        return str(n)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}PB"

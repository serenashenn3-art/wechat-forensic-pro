#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WeChat Forensic Extractor Pro — 向后兼容入口
v2.0.2 起,主实现已迁移至 wechat_forensic/ 包。
此文件保留,仅作为旧版 `python wechat_forensic_pro.py` 的兼容入口。
推荐使用: `wechat-forensic` (安装后) 或 `python -m wechat_forensic.cli`
"""

import sys
import warnings

warnings.warn(
    "wechat_forensic_pro.py 已弃用, 请改用 'wechat-forensic' 命令或 'python -m wechat_forensic.cli'",
    DeprecationWarning,
    stacklevel=2,
)

from wechat_forensic.cli import main

if __name__ == "__main__":
    sys.exit(main())

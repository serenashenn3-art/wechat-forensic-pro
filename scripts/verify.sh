#!/usr/bin/env bash
# 一次性跑完 lint + test + CLI smoke
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> 1/4 ruff"
if command -v ruff >/dev/null 2>&1; then
    ruff check wechat_forensic/ tests/
else
    echo "(ruff 未安装,跳过)"
fi

echo "==> 2/4 pytest"
pytest tests/ -v --cov=wechat_forensic --cov-report=term-missing

echo "==> 3/4 CLI --version"
python3 -m wechat_forensic.cli --version

echo "==> 4/4 CLI --help"
python3 -m wechat_forensic.cli --help | head -5

echo "==> ALL OK"

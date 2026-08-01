#!/usr/bin/env bash
# scripts/sync_agent_compat.sh
#
# 同步 AGENTS.md 到所有 AI Agent 兼容性文件
# ------------------------------------------------------------
# 背景 (v2.0.7):
#   早期版本使用 symlink 指向 AGENTS.md,但 symlink 在 GitHub Web 界面
#   会被渲染为 9 字节占位符,看起来"文件是空的"。v2.0.7 改为普通文件
#   副本(mirror),并用本脚本保持内容一致。
#
# 用法:
#   bash scripts/sync_agent_compat.sh           # 直接同步
#   bash scripts/sync_agent_compat.sh --check  # 只检查,不修改,非 0 退出 = 有漂移
#
# 同步目标 (与 AGENTS.md 内容完全一致):
#   - AGENT.md       (单数,向下兼容某些只认单数的工具)
#   - CLAUDE.md      (Anthropic Claude Code / Cursor Claude)
#   - CODEX.md       (OpenAI Codex)
#   - GEMINI.md      (Google Gemini CLI)
#   - .cursorrules   (Cursor 旧版规则文件名)
#   - .cursor/rules  (Cursor 新版规则文件)
# ------------------------------------------------------------
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$ROOT/AGENTS.md"
TARGETS=(
  "AGENT.md"
  "CLAUDE.md"
  "CODEX.md"
  "GEMINI.md"
  ".cursorrules"
  ".cursor/rules"
)

if [[ ! -f "$SRC" ]]; then
  echo "ERROR: source not found: $SRC" >&2
  exit 2
fi

CHECK_ONLY=0
for arg in "$@"; do
  case "$arg" in
    --check) CHECK_ONLY=1 ;;
    -h|--help)
      sed -n '2,30p' "$0"
      exit 0
      ;;
    *) echo "Unknown arg: $arg" >&2; exit 2 ;;
  esac
done

# 计算源文件 SHA-256
SRC_SHA="$(shasum -a 256 "$SRC" | awk '{print $1}')"
DRIFT=0

for t in "${TARGETS[@]}"; do
  DEST="$ROOT/$t"
  if [[ -L "$DEST" ]]; then
    echo "WARN: $t is still a symlink, removing"
    [[ "$CHECK_ONLY" -eq 1 ]] || rm "$DEST"
  fi
  if [[ ! -f "$DEST" ]]; then
    if [[ "$CHECK_ONLY" -eq 1 ]]; then
      echo "DRIFT: $t missing"
      DRIFT=1
      continue
    fi
    cp "$SRC" "$DEST"
    echo "CREATED: $t"
    continue
  fi
  DEST_SHA="$(shasum -a 256 "$DEST" | awk '{print $1}')"
  if [[ "$SRC_SHA" != "$DEST_SHA" ]]; then
    if [[ "$CHECK_ONLY" -eq 1 ]]; then
      echo "DRIFT: $t differs from AGENTS.md"
      DRIFT=1
    else
      cp "$SRC" "$DEST"
      echo "SYNCED: $t"
    fi
  else
    echo "OK: $t"
  fi
done

if [[ "$CHECK_ONLY" -eq 1 && "$DRIFT" -ne 0 ]]; then
  echo
  echo "Detected content drift. Run: bash scripts/sync_agent_compat.sh" >&2
  exit 1
fi

echo
echo "Done. Source SHA-256: $SRC_SHA"

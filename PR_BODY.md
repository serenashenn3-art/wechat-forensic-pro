# [wechat-forensic-pro] v2.0.2 — 重构为标准 Python 包 + AGENTS.md 多工具兼容

## 改了什么

1. **代码重构**: 1000+ 行单体脚本拆为 `wechat_forensic/` Python 包(12 个职责单一模块)
2. **新标准入口**: `pyproject.toml` 注册 `wechat-forensic` console_script
3. **AI 工具兼容性**: 新增 `AGENTS.md` + 6 个符号链接(`AGENT.md` / `CLAUDE.md` / `CODEX.md` / `GEMINI.md` / `.cursorrules` / `.cursor/rules`),Claude Code / OpenAI Codex / Cursor / Windsurf / Gemini CLI / Aider / Trae / Kimi Work / Devin / Jules 等 60+ 工具打开项目自动读取规范
4. **测试**: `tests/` 21 个 pytest 用例全绿,覆盖 v2.0.1 修复的 7 个关键 bug
5. **CI**: `.github/workflows/tests.yml` 三平台 × 三 Python 版本;`lint.yml` ruff 检查
6. **社区设施**: Issue 模板 (bug / feature request)、`CONTRIBUTING.md`、`SECURITY.md`

## 为什么改

- 旧版单体脚本对人类不友好,改一行要扫 1000+ 行
- AI 工具读 `AGENTS.md` 后可以自动理解项目规范、运行测试、生成合规代码 — 让 Claude / Codex / Trae / Kimi 等都能用
- 测试覆盖了 v2.0.1 修复的 bug,防止回归

## 影响

- **API 层面**:**不破坏兼容**。`wechat_forensic_pro.py` 保留为薄壳,旧 `python wechat_forensic_pro.py ...` 仍可用,只发 `DeprecationWarning`
- **推荐用法**:
  - `pip install -e ".[all]"` 后 `wechat-forensic --help`
  - 或 `python -m wechat_forensic.cli --help`

## 验证

```bash
$ pytest tests/ -v
============================== 21 passed in 0.54s ==============================

$ python -m wechat_forensic.cli --version
wechat-forensic 2.0.2

$ python -m wechat_forensic.cli --help
usage: wechat-forensic [-h] [--mode {quick,forensic}] ...
```

## 根因 (为什么 v2.0.1 → v2.0.2)

v2.0.1 修了 7 个 bug 但没补测试,没拆包,没 AI 工具适配。v2.0.2 是把"能用"升级到"可维护 + AI 协作友好"。

## 法律声明

本项目仅供合法授权场景使用(司法鉴定 / 企业合规 / 本人数据 / 学术研究)。详见 `LICENSE` 与 `AGENTS.md` 顶部声明。

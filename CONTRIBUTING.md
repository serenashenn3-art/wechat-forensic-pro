# 欢迎贡献

感谢你考虑为 WeChat Forensic Extractor Pro 贡献代码!

## ⚠️ 提交前必读

1. **本项目仅服务于合法取证场景**。任何用于未授权设备取证的代码、参数、文档、讨论都将被拒绝。
2. **绝不要**提交任何真实微信数据、镜像、压缩包、报告文件。
3. **绝不要**删除或弱化 `AGENTS.md` / `LICENSE` 中的法律声明。

## 流程

1. Fork → 创建分支 `codex/<short-desc>`
2. 阅读 `AGENTS.md`(Agent 必读 / 也是贡献者必读)
3. 修改代码 + 在 `tests/` 补测试
4. 本地跑通 `pytest tests/ -v` 和 `python -m wechat_forensic.cli --help`
5. 提交 PR,标题格式 `[wechat-forensic-pro] <描述>`

## 提交流程细则

见 `AGENTS.md` 的 "提交流程" 章节。

## Code of Conduct

- 尊重他人, 对事不对人
- 不接受任何试图绕过法律声明的"创意修改"
- 维护者有权拒绝任何可疑 PR,无需解释

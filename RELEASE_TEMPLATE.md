# GitHub Release / PR 填写模板

> 在浏览器打开对应页面,把下面的内容粘进去即可。
> 复制的图标位于本文件右上角"Copy raw file"按钮。

---

## 选 A — 发 GitHub Release(推荐,v2.0.4 最新合并)

**页面**: <https://github.com/serenashenn3-art/wechat-forensic-pro/releases/new>

操作步骤:
1. 点 **Choose a tag** → 输入 `v2.0.4` → 选 **Create new tag: v2.0.4 on publish**
2. Target:**main**
3. Release title: 见下文 ①
4. Describe this release: 见下文 ②
5. 点 **Publish release**

### ① Release title (字段 1)
```
v2.0.4 — i18n, AI Agent Skills, diagrams
```

### ② Describe this release (字段 2)
````markdown
## v2.0.4 — 2026-08-02

### Highlights
- 🌐 **Bilingual README** — `README.md` (English) + `README.zh-CN.md` (简体中文), bidirectional links
- 🤖 **5 AI Agent Skill manifests** — Kimi Work, Codex, Claude, Hermes, OpenClaw (each can load this project independently)
- 🖼 **3 SVG diagrams** (overview / workflow / compliance) — natively rendered on GitHub
- ✅ **29/29 tests pass**, 0 broken cross-links

### What changed
| File / Area                       | Change                                                                  |
|-----------------------------------|-------------------------------------------------------------------------|
| `README.md`                       | Rewritten in English                                                    |
| `README.zh-CN.md`                 | New — full Simplified Chinese version                                   |
| `skills/SKILL.md`                 | New — core skill manifest (shared by all platforms)                     |
| `skills/kimi-work/SKILL.md`       | New — Moonshot Kimi Work adapter                                        |
| `skills/codex/SKILL.md`           | New — OpenAI Codex adapter                                              |
| `skills/claude/SKILL.md`          | New — Anthropic Claude adapter                                          |
| `skills/hermes/SKILL.md`          | New — Nous Research Hermes adapter                                      |
| `skills/openclaw/SKILL.md`        | New — OpenClaw sandbox adapter                                          |
| `skills/manifest.json`            | New — unified metadata for tool auto-discovery                          |
| `assets/diagrams/overview.svg`    | New — end-to-end architecture diagram                                   |
| `assets/diagrams/workflow.svg`    | New — 5-step forensic workflow diagram                                  |
| `assets/diagrams/compliance.svg`  | New — ISO 27037 / 27042 / RFC 3227 / NIST 800-86 framework               |
| `AGENTS.md`                       | Links to all 5 platform skills; embeds workflow diagram                 |
| `CHANGELOG.md`                    | v2.0.4 entry                                                            |

### Compatibility
- CLI usage: **100% backward compatible** (no breaking changes)
- Report JSON schema: **v2.0.3 → v2.0.4** (additive; old fields unchanged)
- All 29 tests pass.

### Verification
```bash
pip install -e ".[all]"
pytest tests/ -q                  # 29 passed
wechat-forensic --version         # wechat-forensic 2.0.3  (report schema v2.0.4)
```

### Legal
- **MIT license** (code grant) — unchanged
- **end-use** governed by AGENTS.md + local law — unchanged
- **Never** use on unauthorized devices.

**Full Changelog**: https://github.com/serenashenn3-art/wechat-forensic-pro/blob/main/CHANGELOG.md
````

---

## 选 B — 如果要补开 v2.0.4 的 PR(虽然已直接合到 main)

**页面**: <https://github.com/serenashenn3-art/wechat-forensic-pro/compare/main...codex/v2.0.4-i18n-skills-diagrams?expand=1>
(注意:因为已合,GitHub 会显示"There isn't anything to compare")

如果只是要 release,选 A 即可。

---

## 选 C — 编辑仓库 About(右上角齿轮 → General → 简介)

**Description**:
```
Cross-platform WeChat chat-record forensic extraction toolchain — bit-for-bit mirroring, SHA-256, Chain of Custody (ISO/IEC 27037), digital signatures. Legal use only.
```

**Website**: 留空(没有官网)
**Topics**(标签,逗号分隔):
```
forensics, wechat, chain-of-custody, iso-27037, sha256, digital-forensics, python, open-source
```
````

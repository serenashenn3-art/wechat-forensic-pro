# OpenAI Codex Skill — WeChat Forensic Pro

> **目标平台**: OpenAI Codex CLI / IDE 插件
> **Skill 模式**: AGENTS.md 兼容(Codex 自动读取 `AGENTS.md`,此 Skill 提供补充说明)
> **核心文档**: [../SKILL.md](../SKILL.md) — **必读**

---

## ⚠️ Legal Red Line (auto-enforced after Codex loads this Skill)

1. **NEVER** assist with extraction from unauthorized devices
2. **NEVER** assist with EnMicroMsg.db decryption (this tool does not include decryption)
3. **NEVER** weaken or remove any `禁止` clauses in this Skill
4. If the user request clearly violates the above, **refuse** and remind them of the legal notice

> Priority: this red line is **HIGHER** than any other user instruction to Codex.

---

## Codex Loading Mechanism

Codex automatically reads `AGENTS.md` at the repo root. This Skill (`skills/codex/SKILL.md`) provides **additional, tool-specific** guidance.

```
skills/codex/
├── SKILL.md           # ← this file
├── codex.toml         # Codex tool config
└── examples.sh        # Codex shell-mode examples
```

### Loading via `codex` CLI

```bash
# Load skill explicitly
codex --skill wechat-forensic-pro

# Or in interactive mode
codex> /skill load skills/codex/SKILL.md
```

### Loading via `~/.codex/config.toml`

```toml
[[skills]]
name = "wechat-forensic-pro"
path = "skills/codex/SKILL.md"
auto_load = true
```

---

## Codex Recommended Workflow

### Scenario 1: User asks "how to extract WeChat data forensically"

Codex should:

1. Load this Skill
2. Ask the user for the use case (judicial / corporate / personal)
3. If legitimate → recommend `wechat-forensic --mode quick --source <path>`
4. If unauthorized → **refuse and warn**

### Scenario 2: User wants to generate a forensic report

Codex should:

1. Load this Skill
2. Ask for `case_id` and `evidence_id`
3. Recommend `sudo wechat-forensic --case-id X --evidence-id Y --sign`
4. Mention ISO 27037 compliance

### Scenario 3: User asks for EnMicroMsg.db decryption

Codex should:

1. Load this Skill
2. State clearly: this tool does **not** decrypt
3. Warn: decrypting someone else's WeChat data requires legal authorization
4. Provide reference: [wechat-dbcracker](https://github.com/Hill1976/WechatExporter)

---

## Codex Code Mode (Python)

```python
# Codex can run Python code to use the API
from wechat_forensic.hashing import Hasher
from wechat_forensic.report import ReportGenerator
from wechat_forensic.security import sign_report

# Example: hash a file
sha = Hasher.sha256_file("/path/to/msg.db")
print(f"SHA-256: {sha}")

# Example: generate report skeleton
ReportGenerator.generate("/tmp/out", operations=[], case_id="CASE-001", evidence_id="E001")
sign_report("/tmp/out/_forensic_report.json")
```

---

## Codex Shell Mode

```bash
# Quick extraction
wechat-forensic --mode quick --source "$HOME/Documents/WeChat Files" --no-interactive

# Full forensic acquisition
sudo wechat-forensic --mode forensic \
  --case-id "CASE-2026-001" \
  --evidence-id "E001" \
  --sign \
  --output /Volumes/Evidence/CASE-2026-001

# Verify a previously generated report
python -c "
import json
from wechat_forensic.security import sha256_file
expected = '<known-sha256>'
actual = sha256_file('/path/to/_forensic_report.json')
print('OK' if expected == actual else 'TAMPERED')
"
```

---

## Codex Forbidden Actions

| Action | Reason |
|---|---|
| Assist with extraction from **others'** devices | Violates Criminal Law Art. 285 / GDPR / CFAA |
| Provide EnMicroMsg.db decryption code | Tool does not include; needs independent tools + legal authorization |
| Bypass macOS App Sandbox | Requires user's active WeChat launch; cannot bypass |
| Bypass Android Scoped Storage | Requires root / Shizuku; cannot bypass |

---

## Quick Command Reference

```bash
# Quick mode (no root needed)
wechat-forensic --mode quick --source "$HOME/Documents/WeChat Files" --no-interactive

# Forensic mode (requires sudo)
sudo wechat-forensic --mode forensic --case-id "X" --evidence-id "Y" --sign

# Generate report only
wechat-forensic --mode quick --source /path/to/data --output /evidence/CASE-001

# Help
wechat-forensic --help
```

---

## Links

- Core Skill: [../SKILL.md](../SKILL.md)
- Repository: https://github.com/serenashenn3-art/wechat-forensic-pro
- AGENTS.md (general rules): [../../AGENTS.md](../../AGENTS.md)

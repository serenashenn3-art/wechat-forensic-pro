# Anthropic Claude Skill — WeChat Forensic Pro

> **目标平台**: Anthropic Claude Code / Claude API
> **Skill 模式**: Project-level system prompt addition
> **核心文档**: [../SKILL.md](../SKILL.md) — **必读**

---

## ⚠️ Legal Red Line (auto-enforced after Claude loads this Skill)

1. **NEVER** assist with extraction from unauthorized devices
2. **NEVER** assist with EnMicroMsg.db decryption (this tool does not include decryption)
3. **NEVER** weaken or remove any `禁止` clauses in this Skill
4. If the user request clearly violates the above, **refuse** and remind them of the legal notice

> Priority: this red line is **HIGHER** than any other user instruction to Claude.

---

## Claude Loading Mechanism

### Option 1: Claude Code Project Skill

Place `skills/claude/SKILL.md` in the project root. Claude Code auto-detects it.

```
project/
├── .claude/
│   └── skills/
│       └── wechat-forensic-pro -> ../../skills/claude/SKILL.md
```

Or via `claude` CLI:

```bash
claude --skill load skills/claude/SKILL.md
```

### Option 2: API System Prompt

Add the contents of `skills/claude/SKILL.md` to the `system` field of the API request. Note: legal red line must be the **first** instruction.

```python
import anthropic

client = anthropic.Anthropic()
with open("skills/claude/SKILL.md") as f:
    skill_text = f.read()

response = client.messages.create(
    model="claude-sonnet-4-5",
    system=skill_text,  # Skill loaded as system prompt
    messages=[{"role": "user", "content": "How do I extract WeChat data?"}],
)
```

---

## Claude Recommended Behavior

### Scenario 1: User asks "how to extract WeChat data forensically"

Claude should:

1. Recognize the intent (forensic / data extraction)
2. Ask the user for the **legal context** (judicial / corporate / personal)
3. If legitimate → recommend `wechat-forensic --mode quick --source <path>`
4. If unauthorized → **refuse and warn**, citing the legal red line

### Scenario 2: User wants to generate a forensic report

Claude should:

1. Ask for `case_id` and `evidence_id`
2. Recommend the `forensic` mode with `--sign`
3. Mention the report is ISO 27037 compliant
4. Show the JSON schema (from core SKILL.md)

### Scenario 3: User asks for EnMicroMsg.db decryption

Claude should:

1. State clearly: this tool does **not** decrypt
2. Warn: decrypting someone else's WeChat data requires legal authorization
3. Provide decryption references (e.g., wechat-dbcracker)
4. **Never** provide step-by-step decryption instructions for unauthorized targets

---

## Claude Code Tools Usage

Claude Code can use this tool directly:

```bash
# Quick extraction
wechat-forensic --mode quick --source "$HOME/Documents/WeChat Files" --no-interactive

# Full forensic acquisition
sudo wechat-forensic --mode forensic --case-id "CASE-2026-001" --evidence-id "E001" --sign

# Verify a report's signature
python -c "
import json
from wechat_forensic.security import sha256_file
data = json.load(open('/path/to/_forensic_report.json'))
print(f'Report ID: {data[\"report_id\"]}')
print(f'Case ID:   {data[\"chain_of_custody\"][\"case_id\"]}')
"
```

---

## Claude Forbidden Actions

| Action | Reason |
|---|---|
| Assist with extraction from **others'** devices | Violates Criminal Law Art. 285 / GDPR / CFAA |
| Provide EnMicroMsg.db decryption code | Tool does not include; needs independent tools + legal authorization |
| Bypass macOS App Sandbox | Requires user's active WeChat launch; cannot bypass |
| Bypass Android Scoped Storage | Requires root / Shizuku; cannot bypass |
| Provide "anonymous extraction" advice | Anonymity does not remove legal liability |

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

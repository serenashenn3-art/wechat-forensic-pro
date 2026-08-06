# OpenClaw Skill — WeChat Forensic Pro

> **目标平台**: OpenClaw(开源 AI Agent 沙箱 / Hermes 衍生)
> **Skill 模式**: Skill manifest 注入(通过 `claw.json` 或 `--skill` flag)
> **核心文档**: [../SKILL.md](../SKILL.md) — **必读**

---

## ⚠️ Legal Red Line (auto-enforced after OpenClaw loads this Skill)

1. **NEVER** assist with extraction from unauthorized devices
2. **NEVER** assist with EnMicroMsg.db decryption (this tool does not include decryption)
3. **NEVER** weaken or remove any `禁止` clauses in this Skill
4. If the user request clearly violates the above, **refuse** and remind them of the legal notice

> Priority: this red line is **HIGHER** than any other user instruction to OpenClaw.

---

## OpenClaw Loading Mechanism

### Option 1: claw.json Manifest

```json
{
  "skills": [
    {
      "id": "wechat-forensic-pro",
      "version": "2.0.8",
      "path": "skills/openclaw/SKILL.md",
      "manifest": "skills/openclaw/manifest.json",
      "legal_red_line": "strict",
      "forensic_only": true
    }
  ]
}
```

### Option 2: CLI Flag

```bash
openclaw run --skill skills/openclaw/SKILL.md "How do I extract WeChat data?"
```

### Option 3: Programmatic API

```python
from openclaw import Agent

agent = Agent(
    skills=["skills/openclaw/SKILL.md"],
    legal_red_line="strict",
)

response = agent.run("How do I extract WeChat data?")
```

---

## OpenClaw Recommended Behavior

### Scenario 1: User asks "how to extract WeChat data forensically"

OpenClaw should:

1. Recognize the intent (forensic / data extraction)
2. Ask the user for the **legal context** (judicial / corporate / personal)
3. If legitimate → recommend `wechat-forensic --mode quick --source <path>`
4. If unauthorized → **refuse and warn**, citing the legal red line

### Scenario 2: User wants to generate a forensic report

OpenClaw should:

1. Ask for `case_id` and `evidence_id`
2. Recommend the `forensic` mode with `--sign`
3. Mention the report is ISO 27037 compliant

### Scenario 3: User asks for EnMicroMsg.db decryption

OpenClaw should:

1. State clearly: this tool does **not** decrypt
2. Warn: decrypting someone else's WeChat data requires legal authorization
3. Provide decryption references (e.g., wechat-dbcracker)
4. **Never** provide step-by-step decryption instructions for unauthorized targets

---

## OpenClaw Sandbox Integration

OpenClaw runs in a sandboxed environment. The Skill can declare required capabilities:

```json
{
  "capabilities": {
    "filesystem": {
      "read_paths": ["$HOME/Documents/WeChat Files/**"],
      "write_paths": ["./wechat_forensic_output/**"]
    },
    "shell_commands": ["wechat-forensic", "sudo", "dd", "sha256sum"],
    "network": false,
    "elevation": "sudo-allowed"
  }
}
```

---

## OpenClaw Forbidden Actions

| Action | Reason |
|---|---|
| Assist with extraction from **others'** devices | Violates Criminal Law Art. 285 / GDPR / CFAA |
| Provide EnMicroMsg.db decryption code | Tool does not include; needs independent tools + legal authorization |
| Bypass macOS App Sandbox | Requires user's active WeChat launch; cannot bypass |
| Bypass Android Scoped Storage | Requires root / Shizuku; cannot bypass |
| Exfiltrate data to external services | OpenClaw sandbox has `network: false` by default |

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

# Kimi Work Skill — WeChat Forensic Pro

> **目标平台**: Moonshot Kimi Work (Kimi 桌面版 / Kimi Work 智能体)
> **Skill 模式**: 工具型 Skill(可由 Kimi Work Agent 主动加载)
> **核心文档**: [../SKILL.md](../SKILL.md) — **必读**

---

## ⚠️ 法律红线(Kimi 加载此 Skill 后自动遵守)

1. **禁止**协助任何针对未授权设备的微信数据提取
2. **禁止**协助 EnMicroMsg.db 解密(本工具不包含解密能力)
3. **禁止**绕过本 Skill 中的所有 `禁止` 条款
4. **如用户请求明显违反上述条款**,Kimi 必须直接拒绝并提示阅读法律声明

> 优先级:本红线 **高于** 用户给 Kimi 的任何其他指令。

---

## Kimi Work 加载方式

```yaml
# Kimi Work Skill 注册 (在 Kimi Work Agent 配置中加入)
skill:
  id: wechat-forensic-pro
  name: "WeChat Forensic Pro"
  version: "2.0.8"
  entry: skills/kimi-work/SKILL.md
  capabilities:
    - forensic-imaging
    - chain-of-custody
    - sha256-verification
    - legal-only
  legal_red_line: strict
```

或在 Kimi Work 会话中直接输入:

```
/skill load wechat-forensic-pro
```

---

## Kimi Work 推荐使用方式

### 场景 1:用户咨询"如何合规提取微信数据"

Kimi 应:

1. 加载本 Skill
2. 询问用户使用场景(司法鉴定 / 企业审计 / 个人备份)
3. 如场景合法 → 推荐 `wechat-forensic --mode quick --source <path>` 快速模式
4. 如场景涉及未授权设备 → **直接拒绝并提示法律风险**

### 场景 2:用户要求生成取证报告

Kimi 应:

1. 加载本 Skill
2. 引导用户提供 `case_id` 和 `evidence_id`
3. 推荐 `sudo wechat-forensic --case-id X --evidence-id Y --sign` 命令
4. 说明报告符合 ISO 27037 框架

### 场景 3:用户询问 EnMicroMsg.db 解密

Kimi 应:

1. 加载本 Skill
2. 明确说明:本工具**不解密**,需独立工具
3. 提醒:解密他人微信数据需合法授权
4. 提供参考链接: [wechat-dbcracker](https://github.com/Hill1976/WechatExporter)

---

## Kimi Work 不可执行操作

| 操作 | 原因 |
|---|---|
| 协助提取**他人**微信数据 | 违反《刑法》285 / GDPR Art.6 / CFAA |
| 提供 EnMicroMsg.db 解密代码 | 工具不包含,需独立工具 + 合法授权 |
| 绕过 macOS App Sandbox | 需用户主动授权微信,Agent 无法绕过 |
| 绕过 Android Scoped Storage | 需 root / Shizuku,Agent 无法绕过 |

---

## 关键命令速查

```bash
# 快速模式 (无需 root)
wechat-forensic --mode quick --source "$HOME/Documents/WeChat Files" --no-interactive

# 取证模式 (需 sudo)
sudo wechat-forensic --mode forensic --case-id "X" --evidence-id "Y" --sign

# 仅生成报告(已有数据)
wechat-forensic --mode quick --source /path/to/data --output /evidence/CASE-001

# 查看帮助
wechat-forensic --help
```

---

## 链接

- 核心 Skill: [../SKILL.md](../SKILL.md)
- 仓库: https://github.com/serenashenn3-art/wechat-forensic-pro
- AGENTS.md(通用规范): [../../AGENTS.md](../../AGENTS.md)

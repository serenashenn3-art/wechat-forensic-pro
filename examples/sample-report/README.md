# 报告样例 — `examples/sample-report/`

> **目的**: 让读者**一眼**看清 `wechat-forensic` 实际输出长什么样 —
> 用于模板、对照 schema、向客户 / 法官 / 评审做"产出预览"。
>
> **重要声明**: 本样例中**所有**标识符(案件号、证据号、wxid、
> 设备路径、文件路径、哈希值、人名、聊天内容)都是**完全合成的**
> mock 数据,**不来自任何真实案件、不对应任何真实个人**。
> 哈希值是符合 SHA-256 长度但**不指向任何真实文件**的随机字符串。

## 文件清单

| 文件 | 用途 | 阅读者 |
|---|---|---|
| `README.md` | 本文件 — 阅读指引 | 所有人 |
| `_forensic_report.json` | 机器可读 — 完整 schema (v2.0.8) | 后端 / 审计系统 |
| `_forensic_report.txt` | 人类可读 — 排版后文本版 | 法官 / 律师 / 当事人 |
| `_signature.json` | HMAC 签名 + 密钥指纹 | 取证复核人 |
| `_forensic_manifest.json` | 每文件 SHA-256 清单 | 完整性验证 |
| `operations_summary.md` | 操作时间线 | 案件复核人 |
| `chat_excerpt_redacted.txt` | 脱敏聊天摘录 (mock) | 评估聊天内容还原度 |

## 如何用这个样例

1. **照搬 schema**: 用 `_forensic_report.json` 作为你自己案件报告的
   模板,只替换值,不改结构
2. **校验输出**: 跑完一次 `wechat-forensic` 后,把自己的
   `_forensic_report.json` 跟这个样例做 diff,看字段是否一致
3. **写代码解析**: 如果你要做"批量报告归档 / 自动复核",用样例
   `_forensic_report.json` 作为测试 fixture
4. **给客户预览**: 把 `_forensic_report.txt` 给客户看,
   演示"最终报告长这样"
5. **司法培训**: 把整个目录作为教学样例,演示"一份合格的
   司法取证报告应当包含哪些字段"

## 关键字段速查

| 字段 | 在哪里 | 用途 |
|---|---|---|
| `case_id` / `evidence_id` | `_forensic_report.json` 顶层 | 案件 / 证据唯一标识 |
| `chain_of_custody.acquisition.write_blocking` | 同上 | 写保护设备记录(司法采信核心) |
| `chain_of_custody.transfer_chain` | 同上 | 证据流转链(每次经手签名) |
| `operations[].sha256` | 同上 | 每个操作步骤产物的 SHA-256 |
| `_signature.json.signature_b64` | 签名文件 | 整个报告的 HMAC 签名 |
| `_signature.json.key_fingerprint_sha256` | 签名文件 | **密钥指纹**(可核验身份不暴露明文) |

## 注意

- **所有哈希值都是 mock 的** — 不能用它们去验证任何真实文件
- **聊天摘录(`chat_excerpt_redacted.txt`)完全是虚构对话** —
  不反映任何真实人物的言论
- **写保护设备型号、操作系统、Python 版本**都是样例值 —
  实际案件必须写真实信息

---

更多关于 schema 的定义见:
- `wechat_forensic/report.py` — 报告生成器
- `wechat_forensic/security.py` — Chain of Custody 模板 + 签名逻辑
- `README.md` § "Output Format"

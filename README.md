# WeChat Forensic Extractor Pro

> 跨平台微信聊天记录取证提取工具链 v2.0
> 位对位镜像 · 哈希校验 · 证据链保全 · 云端备份

![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-blue)
![Python](https://img.shields.io/badge/python-3.8%2B-green)
![License](https://img.shields.io/badge/license-MIT-orange)
![Purpose](https://img.shields.io/badge/purpose-Authorized%20Forensics%20Only-red)

## ⚠️ 法律声明 / Legal Notice

**本工具仅供合法授权场景使用**,包括但不限于:

- 司法鉴定机构受委托的电子数据取证
- 企业内部合规审计(经员工授权)
- 应急响应与数据恢复
- 个人信息备份(本人数据)
- 学术研究与教学演示

**严禁**用于任何未授权的设备取证、私人偷拍取证、商业窃密或其他违反
《中华人民共和国刑法》《数据安全法》《个人信息保护法》的行为。
使用本工具即代表您已阅读并同意本条款,作者不承担任何滥用责任。

---

## ✨ 核心能力

| 模块 | 能力 |
|---|---|
| 设备扫描 | 逻辑/物理磁盘、iTunes 备份、ADB 设备识别 |
| 位对位镜像 | `dd` 整盘镜像、Python 逐块复制、取证级目录镜像 |
| 微信定位 | 自动扫描 Windows / macOS / Linux 默认路径 + 自定义路径 |
| 数据提取 | 保留元数据 (mtime/atime/ctime),逐文件 SHA-256 |
| 证据链报告 | JSON + 可读文本双格式,记录每一步哈希、操作者、时间戳 |
| 压缩加密 | 支持 AES 加密 zip (`pyzipper`) |
| 云端备份 | 百度网盘 (`bypy`) / 阿里云 OSS (`oss2`) |

## 📁 微信数据默认路径

| 平台 | 路径 |
|---|---|
| Windows | `%USERPROFILE%\Documents\WeChat Files` |
| macOS | `~/Library/Containers/com.tencent.xinWeChat/...` |
| Linux | `~/.config/wechat` |
| iOS 备份 | `~/Library/Application Support/MobileSync/Backup/<40位hash>/` |
| Android | `/Android/data/com.tencent.mm/MicroMsg` |

## 🚀 快速开始

```bash
# 1. 克隆
git clone https://github.com/<your-username>/wechat-forensic-pro.git
cd wechat-forensic-pro

# 2. 安装依赖
pip install -r requirements.txt

# 3. 基础提取 (取证模式,需要 root/admin)
sudo python3 wechat_forensic_pro.py

# 4. 快速模式 (跳过磁盘镜像)
python3 wechat_forensic_pro.py --mode quick

# 5. 指定源路径
python3 wechat_forensic_pro.py --source "/path/to/WeChat Files"

# 6. 加密压缩
python3 wechat_forensic_pro.py --zip-password "YourStrongPass!"

# 7. 上传阿里云 OSS
python3 wechat_forensic_pro.py --upload aliyun
```

### 完整参数

```
--mode {quick,forensic}    # quick=直接提取 | forensic=含位对位镜像(默认)
--source PATH              # 手动指定微信数据目录
--mirror-disk PATH         # 物理磁盘 (如 /dev/sdb 或 \\.\PhysicalDrive0)
--output DIR               # 输出目录 (默认 ./wechat_forensic_output)
--zip-password PWD         # 压缩包密码 (AES 加密)
--upload {baidu,aliyun,none}  # 云端上传目标
--no-interactive           # 非交互模式
```

## 📦 输出结构

```
wechat_forensic_output/
├── mirrors/                      # 位对位镜像
│   └── disk_mirror_20260801_xxxxxx.img
├── PC_wxid_xxxxx/                # PC 微信提取
│   ├── Msg/                      # 数据库
│   ├── FileStorage/              # 文件
│   └── config/
├── Mobile_ios_xxxxx/             # iOS 备份提取
├── _forensic_manifest.json       # 整体清单
├── _forensic_report.json         # 取证报告 (结构化)
├── _forensic_report.txt          # 取证报告 (可读)
├── forensic_log.txt              # 操作日志
└── wechat_forensic_output_*.zip  # 压缩包 + SHA-256
```

## 🔐 证据链保全

每一步操作都会记录:

- ✅ **哈希值** (SHA-256, 块大小 4MB)
- ✅ **时间戳** (ISO 8601)
- ✅ **操作人员** (`getpass.getuser()`)
- ✅ **主机名 / 操作系统** (`platform.node()` / `platform.platform()`)
- ✅ **Python 版本** (报告兼容性)

**核心原则**: 原始证据不动,所有操作在副本/镜像上进行。

## 🛠️ 修复记录 (相对原版)

| # | 修复 |
|---|---|
| 1 | `_hash_directory` 错误地把路径字符串当文件内容传入 `sha256_file` — 现已改为先哈希相对路径、再哈希文件内容 |
| 2 | 取证文本报告中所有 `\n` 误转义为字面 `\\n` — 修正 |
| 3 | `os.geteuid()` 在 Windows 抛 `AttributeError` — 改为跨平台 `is_admin()` |
| 4 | macOS 物理磁盘扫描逻辑不通 — 改为 `diskutil list` 解析 + 过滤 `s` 结尾的分区 |
| 5 | Windows 磁盘信息 PowerShell 优先,`wmic` 仅作回退 |
| 6 | `input()` 在 `--no-interactive` 时仍会阻塞 — 仅在交互模式调用 |
| 7 | 抽出 `is_admin()` 跨平台工具函数 |

## 📜 许可

MIT License — 见 [LICENSE](LICENSE)

仅供合法授权场景使用,详见顶部法律声明。

# 变更日志

## [2.0.1] - 2026-08-01

### 修复
- `_hash_directory` 错误地把路径字符串当文件内容传入 `sha256_file`,导致目录整体哈希结果无效
- 取证报告 `_forensic_report.txt` 中所有 `\n` 被错误转义为字面 `\\n`,报告无法阅读
- `os.geteuid()` 在 Windows 直接抛 `AttributeError`,改用跨平台 `is_admin()`
- macOS 物理磁盘扫描逻辑不通,改用 `diskutil list` 解析 + 过滤 `s` 结尾的分区
- Windows 磁盘信息优先使用 PowerShell (`Get-CimInstance`),`wmic` 仅作回退
- `--no-interactive` 模式下仍会因 `input()` 阻塞
- `extractor.extract_mobile` 调用 `_copy_with_hash` 时参数顺序不一致

### 改进
- 抽出 `is_admin()` 跨平台工具函数
- 物理磁盘扫描的 Windows 输出新增 size_bytes / interface 字段
- 取证报告 README 增加法律声明和修复记录表

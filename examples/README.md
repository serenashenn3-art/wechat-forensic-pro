# Examples

> 用法示例。所有示例都假设你**已获得合法授权**使用本工具。

## 报告样例

> 📄 [sample-report/](sample-report/) — 一份**完整脱敏**的 mock 取证报告
> 包含 JSON、TXT、HMAC 签名、Manifest、操作时间线、聊天摘录。
> 所有标识符和哈希值都是合成的,仅用于展示 v2.0.8 输出长什么样、
> 校验 schema、对客户 / 法官做预览。
>
> **不要**把这些 mock 哈希用去校验任何真实文件。

## 基础

```bash
# 安装 (含可选依赖)
pip install -e ".[all]"

# 查看版本与帮助
wechat-forensic --version
wechat-forensic --help

# 快速模式 - 仅提取文件不做磁盘镜像
wechat-forensic --mode quick --source "/path/to/WeChat Files"

# 取证模式 (默认) - 含位对位镜像 + 哈希 + 报告
sudo wechat-forensic  # 镜像磁盘需要管理员
```

## 加密压缩

```bash
# AES 加密压缩包
pip install pyzipper
wechat-forensic --zip-password "YourStrongPass!"
```

## 云端上传

```bash
# 阿里云 OSS
export WECHAT_OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
export WECHAT_OSS_BUCKET=my-bucket
# (把上面写到 Config 类的字段里)
wechat-forensic --upload aliyun

# 百度网盘
pip install bypy
bypy info  # 首次需要授权
wechat-forensic --upload baidu
```

## Python API

```python
from wechat_forensic.hashing import Hasher
from wechat_forensic.extractor import Extractor
from wechat_forensic.logger import ForensicLogger

# 1) 计算单个文件哈希
sha = Hasher.sha256_file("/path/to/msg.db")
print(sha)

# 2) 提取整个微信目录
ext = Extractor(ForensicLogger("./log.txt"), out_dir="./out")
ext.extract_pc({
    "wxid": "wxid_abc",
    "path": "/path/to/WeChat Files/wxid_abc",
    "msg": "/path/to/.../Msg",
    "filestorage": "/path/to/.../FileStorage",
    "config": "/path/to/.../config",
})
ext.save_manifest()
```

## CI / 自动化

```bash
# 跑测试
pytest tests/ -v

# 代码风格 (可选)
pip install ruff
ruff check wechat_forensic/ tests/
```

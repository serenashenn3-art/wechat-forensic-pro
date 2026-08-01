# WeChat Forensic Pro — 自定义上传器示例

## 适用版本

v2.0.5 起,云盘上传改为可插拔架构。内置覆盖 6 种主流方式(百度/阿里/S3/WebDAV/SFTP/本地),其余云盘均可通过本目录示例改写或新增。

## 三种扩展方式

| 方式 | 难度 | 适用场景 |
|---|---|---|
| **1. 改写 S3 适配器配置** | 零代码 | 任何 S3 兼容协议(腾讯 COS-S3/七牛 S3/MinIO/自建 Ceph) |
| **2. 改写 WebDAV/SFTP 适配器配置** | 零代码 | 任何 WebDAV 或 SFTP 协议端点 |
| **3. 写插件** | 几十行 Python | SDK 协议特殊(OneDrive Graph / Google Drive / 钉钉云盘 等) |

## 1. S3 兼容 (推荐,90% 场景)

几乎所有主流云盘都提供 S3 兼容 API,只需要换 `endpoint_url`:

```yaml
# ~/.config/wechat-forensic/upload.yaml
s3:
  endpoint_url: https://cos.ap-guangzhou.myqcloud.com   # 腾讯 COS
  region: ap-guangzhou
  bucket: example-1250000000
  access_key: AKIDxxxxxxxxxxxxxxxxxxxx
  secret_key: xxxxxxxxxxxxxxxxxxxxxxxx
  prefix: wechat_forensic/
```

```bash
wechat-forensic --upload s3 --upload-config ~/.config/wechat-forensic/upload.yaml
```

## 2. WebDAV / SFTP

坚果云、Nextcloud、ownCloud、OneDrive 启用 WebDAV 后,直接配 `url/username/password` 即可。

## 3. 写插件

把 `examples/uploaders/tencent_cos.py` 或 `examples/uploaders/qiniu.py` 复制到下面任一目录即可生效:

```
~/.config/wechat-forensic/plugins/uploaders/   # 用户级 (推荐,跨项目)
<wechat-forensic-pro>/uploaders/               # 项目级 (单项目)
```

最小插件模板:

```python
from wechat_forensic.uploader import UploaderBase

class MyCloudUploader(UploaderBase):
    name = "my-cloud"            # CLI 使用的 --upload 值
    display_name = "我的公司云盘"
    required_deps = ["my-sdk"]   # 缺包时给清晰提示

    def upload(self, file, logger=None, config=None):
        # 1) 读 config (dict)
        # 2) 校验必要字段
        # 3) 调用 SDK 上传
        # 4) 失败: return self._return_failure("原因")
        #    成功: return self._return_success("远端路径", {...})
        ...
```

返回值规范:
```python
{
    "success": bool,        # 必填
    "message": str,         # 失败原因 / "OK"
    "remote": str,          # 远端完整路径 (s3:// / oss:// / /mnt/nas/... )
    "algorithm": str,       # uploader name, 自动填充
    ...                      # 任意额外字段 (bucket/key/region/...)
}
```

## 配置文件 schema

`upload.yaml` 结构:

```yaml
# 整体格式: <uploader_name>: <config>
# 同时可放 "default": "<name>" 作为默认 uploader

default: s3

s3:
  endpoint_url: https://...
  region: us-east-1
  bucket: my-bucket
  access_key: AKIA...
  secret_key: xxxx
  prefix: wechat_forensic/

webdav:
  url: https://dav.jianguoyun.com/dav
  username: you@example.com
  password: xxx
  remote_path: /forensic/

local:
  destination_dir: /Volumes/BackupDrive/forensic
  mode: copy   # copy | move | hardlink
```

## 内联环境变量 (无配置文件)

```bash
export WECHAT_FORENSIC_UPLOAD_S3_BUCKET=my-bucket
export WECHAT_FORENSIC_UPLOAD_S3_REGION=ap-shanghai
export WECHAT_FORENSIC_UPLOAD_S3_ACCESS_KEY=AKIA...
export WECHAT_FORENSIC_UPLOAD_S3_SECRET_KEY=xxxx
export WECHAT_FORENSIC_UPLOAD_S3_ENDPOINT_URL=https://...
wechat-forensic --upload s3
```

## 列出当前所有可用上传器

```python
from wechat_forensic.uploader import UploaderRegistry
for u in UploaderRegistry().list():
    star = "*" if u["is_builtin"] else "+"
    print(f'[{star}] {u["name"]:12s} {u["display_name"]} (deps: {u["required_deps"]})')
```

## 列表所有内置协议

| name | 协议 | 依赖包 | 典型服务商 |
|---|---|---|---|
| `baidu` | bypy CLI | bypy | 百度网盘 |
| `aliyun` | OSS SDK | oss2 | 阿里云 OSS |
| `s3` | S3 API | boto3 | AWS S3 / 腾讯 COS / 七牛 S3 / MinIO / 阿里 OSS-S3 / 自建 Ceph |
| `webdav` | WebDAV | webdavclient3 | 坚果云 / Nextcloud / ownCloud / OneDrive(WebDAV 模式) |
| `sftp` | SSH | paramiko | 自建 NAS / 树莓派 / 老旧服务器 |
| `local` | 本地 fs | (无) | NAS 挂载 / USB 移动硬盘 / 第二块硬盘 |

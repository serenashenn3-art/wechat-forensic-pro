"""示例: 七牛云 Kodo 插件 (v2.0.5 插件机制演示)

把这个文件复制到 ~/.config/wechat-forensic/plugins/uploaders/qiniu.py
即可被自动发现。

实际使用需要安装 SDK: pip install qiniu
"""

from wechat_forensic.uploader import UploaderBase


class QiniuUploader(UploaderBase):
    """七牛云 Kodo 对象存储。

    必需配置:
      - access_key
      - secret_key
      - bucket
    可选:
      - prefix (默认 wechat_forensic/)
      - domain (私有空间下载域名,可选)
    """

    name = "qiniu"
    display_name = "七牛云 Kodo"
    required_deps = ["qiniu"]
    config_schema_hint = "access_key, secret_key, bucket, prefix, domain"

    def upload(self, file, logger=None, config=None):
        config = config or {}
        ak = config.get("access_key")
        sk = config.get("secret_key")
        bucket = config.get("bucket")
        prefix = config.get("prefix", "wechat_forensic/").rstrip("/")
        domain = config.get("domain")

        if not (ak and sk and bucket):
            return self._return_failure("七牛云配置缺失 (access_key / secret_key / bucket 必填)")

        try:
            from qiniu import Auth, put_file  # type: ignore
        except ImportError:
            return self._return_failure("未安装 qiniu: pip install qiniu")

        try:
            q = Auth(ak, sk)
            key = f"{prefix}/{file.split('/')[-1]}"
            token = q.upload_token(bucket, key)
            self._log(logger, "info", f"七牛上传 {file} -> {bucket}/{key}")
            ret, info = put_file(token, key, file)
            if info.status_code == 200:
                self._log(logger, "success", f"七牛上传成功: {ret.get('key')}")
                return self._return_success(
                    f"qiniu://{bucket}/{key}",
                    {"bucket": bucket, "key": key, "hash": ret.get("hash")},
                )
            return self._return_failure(f"七牛失败: status={info.status_code}")
        except Exception as e:
            return self._return_failure(f"七牛异常: {e}")

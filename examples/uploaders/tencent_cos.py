"""示例: 腾讯云 COS 插件 (v2.0.5 插件机制演示)

把这个文件复制到以下任一位置即可被自动发现:
  - ~/.config/wechat-forensic/plugins/uploaders/tencent_cos.py   (用户级)
  - <project>/uploaders/tencent_cos.py                            (项目级)

插件无需打包发布,只要类继承 :class:`wechat_forensic.uploader.UploaderBase` 即可。

实际 COS 接入需要安装 SDK: pip install cos-python-sdk-v5
"""

from wechat_forensic.uploader import UploaderBase


class TencentCOSUploader(UploaderBase):
    """腾讯云对象存储 (COS)。

    必需配置:
      - secret_id
      - secret_key
      - region (例: ap-guangzhou)
      - bucket (例: example-1250000000)
    可选:
      - prefix (默认 wechat_forensic/)
    """

    name = "tencent-cos"
    display_name = "腾讯云 COS"
    required_deps = ["cos-python-sdk-v5"]
    config_schema_hint = "secret_id, secret_key, region, bucket, prefix"

    def upload(self, file, logger=None, config=None):
        config = config or {}
        secret_id = config.get("secret_id")
        secret_key = config.get("secret_key")
        region = config.get("region")
        bucket = config.get("bucket")
        prefix = config.get("prefix", "wechat_forensic/").rstrip("/")

        if not (secret_id and secret_key and region and bucket):
            return self._return_failure(
                "腾讯云 COS 配置缺失 (secret_id / secret_key / region / bucket 必填)"
            )

        try:
            from qcloud_cos import CosConfig, CosS3Client  # type: ignore
        except ImportError:
            return self._return_failure(
                "未安装 cos-python-sdk-v5: pip install cos-python-sdk-v5"
            )

        try:
            cos_conf = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key)
            client = CosS3Client(cos_conf)
            key = f"{prefix}/{file.split('/')[-1]}"
            self._log(logger, "info", f"COS 上传 {file} -> cos://{bucket}/{key}")
            client.upload_file(Bucket=bucket, Key=key, LocalFilePath=file)
            self._log(logger, "success", f"腾讯云 COS 上传成功: {key}")
            return self._return_success(
                f"cos://{bucket}/{key}",
                {"bucket": bucket, "key": key, "region": region},
            )
        except Exception as e:
            return self._return_failure(f"腾讯云 COS 失败: {e}")

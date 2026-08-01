"""云端上传(可选)"""

import subprocess
from pathlib import Path


class Uploader:
    @staticmethod
    def baidu(file: str, logger=None) -> bool:
        try:
            if logger:
                logger.info("上传百度云...")
            r = subprocess.run(
                ["bypy", "upload", file, "/wechat_forensic"],
                capture_output=True,
                text=True,
                timeout=600,
            )
            if r.returncode == 0:
                if logger:
                    logger.success("百度云上传成功")
                return True
            if logger:
                logger.error(f"百度云失败: {r.stderr}")
            return False
        except FileNotFoundError:
            if logger:
                logger.error("未安装 bypy: pip install bypy && bypy info")
            return False

    @staticmethod
    def aliyun(file: str, logger=None) -> bool:
        try:
            if logger:
                logger.info("上传阿里云OSS...")
            import oss2  # type: ignore

            from .config import Config

            cfg = Config()
            auth = oss2.Auth(cfg.ALIYUN_ACCESS_KEY, cfg.ALIYUN_SECRET_KEY)
            bucket = oss2.Bucket(auth, cfg.ALIYUN_OSS_ENDPOINT, cfg.ALIYUN_OSS_BUCKET)
            name = f"wechat_forensic/{Path(file).name}"
            bucket.put_object_from_file(name, file)
            if logger:
                logger.success(f"阿里云上传成功: {name}")
            return True
        except ImportError:
            if logger:
                logger.error("未安装 oss2: pip install oss2")
            return False
        except Exception as e:
            if logger:
                logger.error(f"阿里云失败: {e}")
            return False

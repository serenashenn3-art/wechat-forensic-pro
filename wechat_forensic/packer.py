"""压缩 / 加密打包"""

import datetime
import zipfile
from pathlib import Path
from typing import Optional


class Packer:
    @staticmethod
    def zip_dir(
        src: str,
        dst: Optional[str] = None,
        pwd: Optional[str] = None,
        logger=None,
    ) -> str:
        s = Path(src)
        if not dst:
            dst = f"{s.name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        out = Path(dst)

        if logger:
            logger.info(f"开始压缩: {src} -> {dst}")

        if pwd:
            try:
                import pyzipper  # type: ignore

                with pyzipper.AESZipFile(
                    out, "w", pyzipper.ZIP_DEFLATED, encryption=pyzipper.WZ_AES
                ) as zf:
                    zf.setpassword(pwd.encode())
                    for f in s.rglob("*"):
                        if f.is_file():
                            zf.write(f, f.relative_to(s))
                if logger:
                    logger.success(f"加密压缩: {out}")
                return str(out)
            except ImportError:
                if logger:
                    logger.warning("pyzipper 未安装,使用普通压缩")

        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in s.rglob("*"):
                if f.is_file():
                    zf.write(f, f.relative_to(s))

        if logger:
            logger.success(f"压缩完成: {out} ({out.stat().st_size / 1024**3:.2f}GB)")
        return str(out)

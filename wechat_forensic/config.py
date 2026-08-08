"""配置与默认值

微信路径表说明 (2026-08 更新):

PC 端 - Windows
  默认: %USERPROFILE%\\Documents\\WeChat Files\\
  历史: 也可能在 D:\\Documents\\WeChat Files (用户自定义安装目录)

PC 端 - macOS (完整路径,沙盒 Container)
  ~/Library/Containers/com.tencent.xinWeChat/Data/Library/Application Support/com.tencent.xinWeChat/
  说明: 这是 macOS App Sandbox 强制要求的完整路径,不是 typo
  注意: 沙盒内 App 启动时才能访问,直接 ls 可能 Permission Denied

PC 端 - Linux
  默认: ~/.config/wechat
  说明: Linux 版微信由 CrossOver/Wine 运行,实际是 Windows 目录结构
  实际位置取决于启动配置

iOS 备份 (Finder/iTunes)
  位置: ~/Library/Application Support/MobileSync/Backup/<UDID>/
  UDID: Apple 设备唯一标识符, 40 位十六进制 (例: 00008110-... 短横线版
        或 64 位全 hex 的完整 UDID)
  注意: 备份目录名是 UDID 去掉横线的小写 hex
  解密: 加密备份需 --password 参数传入 iTunes 加密密码

Android - /Android/data/ 路径
  Android 11+ (Scoped Storage): /sdcard/Android/data/com.tencent.mm/
    读取受 Scoped Storage 限制,需要:
    1. Root 权限 (adb root + mount -o rw), 或
    2. ADB backup (需微信允许,新版微信已禁用), 或
    3. 通过 Shizuku / 第三方授权工具
  Android 10 及以下: 直接 adb pull 可读
  微信数据库位置: /data/data/com.tencent.mm/MicroMsg/<32位MD5>/EnMicroMsg.db
    读取 /data/data/ 强制需要 root

EnMicroMsg.db 加密
  算法: SQLCipher (AES-256-CBC) + 自定义密钥派生
  密钥: MD5(IMEI + UIN)[0:7]  (IMEI 通常为 32 位 MD5 取前 7 位)
  本工具: 仅做位对位提取,不包含解密逻辑。
  法律注意: 解密他人微信数据仍需合法授权。AGENTS.md 禁止本工具
  协助任何未经授权的解密或提取行为。
"""

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class Config:
    """全局配置"""

    OUTPUT_DIR: str = "./wechat_forensic_output"
    MIRROR_DIR: str = "./wechat_mirrors"
    LOG_FILE: str = "./forensic_log.txt"
    ZIP_PASSWORD: Optional[str] = None
    CHUNK_SIZE: int = 1024 * 1024 * 4  # 4MB

    # 阿里云 OSS (留空跳过)
    ALIYUN_OSS_ENDPOINT: str = ""
    ALIYUN_OSS_BUCKET: str = ""
    ALIYUN_ACCESS_KEY: str = ""
    ALIYUN_SECRET_KEY: str = ""

    WECHAT_PATHS: Dict[str, list] = field(default_factory=dict)
    ITUNES_BACKUP: Dict[str, str] = field(default_factory=dict)
    ANDROID_DATA_PATHS: list = field(default_factory=list)

    def __post_init__(self):
        if not self.WECHAT_PATHS:
            self.WECHAT_PATHS = {
                "Windows": [
                    r"%USERPROFILE%\Documents\WeChat Files",
                    r"D:\Documents\WeChat Files",
                    r"D:\WeChat Files",
                    r"E:\WeChat Files",
                ],
                # macOS: 完整沙盒路径,见模块顶部 docstring
                "Darwin": [
                    "~/Library/Containers/com.tencent.xinWeChat/"
                    "Data/Library/Application Support/com.tencent.xinWeChat",
                ],
                "Linux": [
                    "~/.config/wechat",
                ],
            }
        if not self.ITUNES_BACKUP:
            # 备份目录名 = UDID(40位或64位hex,全小写,无横线)
            self.ITUNES_BACKUP = {
                "Windows": r"%USERPROFILE%\Apple\MobileSync\Backup",
                "Darwin": "~/Library/Application Support/MobileSync/Backup",
            }
        if not self.ANDROID_DATA_PATHS:
            # Android 11+ Scoped Storage 默认不可读,需 root/ADB 授权
            self.ANDROID_DATA_PATHS = [
                # 新版 (Android 11+ Scoped Storage)
                "/sdcard/Android/data/com.tencent.mm/MicroMsg",
                "/storage/emulated/0/Android/data/com.tencent.mm/MicroMsg",
                # 旧版 (Android 10 及以下)
                "/sdcard/tencent/MicroMsg",
                "/storage/emulated/0/tencent/MicroMsg",
                # /data/data 强制需要 root
                "/data/data/com.tencent.mm/MicroMsg",
            ]

"""取证日志系统"""

import logging
import sys


class ForensicLogger:
    def __init__(self, log_file: str):
        self.log_file = log_file
        self.logger = logging.getLogger("wechat_forensic.Forensic")
        self.logger.setLevel(logging.INFO)

        # 避免重复添加处理器; 同时不要污染 root logger
        if self.logger.handlers:
            self.logger.handlers.clear()

        formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        self.logger.addHandler(stream_handler)

        # 不向父 logger 传播,防止重复输出到 root logger
        self.logger.propagate = False

    def info(self, msg):
        self.logger.info(msg)

    def warning(self, msg):
        self.logger.warning(msg)

    def error(self, msg):
        self.logger.error(msg)

    def success(self, msg):
        self.logger.info(f"[OK] {msg}")

    def evidence(self, msg):
        self.logger.info(f"[EVIDENCE] {msg}")

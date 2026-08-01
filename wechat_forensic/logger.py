"""取证日志系统"""

import logging
import sys


class ForensicLogger:
    def __init__(self, log_file: str):
        self.log_file = log_file
        logging.basicConfig(
            level=logging.INFO,
            format="[%(asctime)s] [%(levelname)s] %(message)s",
            handlers=[
                logging.FileHandler(log_file, encoding="utf-8"),
                logging.StreamHandler(sys.stdout),
            ],
        )
        self.logger = logging.getLogger("Forensic")

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

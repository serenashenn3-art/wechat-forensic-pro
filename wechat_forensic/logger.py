"""取证日志系统"""

import hashlib
import logging
import os
import sys


class _ForensicFileHandler(logging.FileHandler):
    """带哈希链的日志处理器,可检测事后篡改。

    每条日志记录追加其前一条日志的 SHA-256(prev_hash + record) 哈希,
    形成简单的链式结构。篡改任意一行后,后续行的 prev_hash 将无法对齐。
    """

    def __init__(self, filename, encoding="utf-8"):
        super().__init__(filename, mode="a", encoding=encoding, delay=False)
        self._prev_hash = self._load_last_hash()

    def _load_last_hash(self) -> str:
        if not os.path.exists(self.baseFilename):
            return "0" * 64
        try:
            with open(self.baseFilename, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in reversed(lines):
                    if "| chain_hash:" in line:
                        return line.strip().rsplit("| chain_hash:", 1)[1].strip()
        except Exception:
            pass
        return "0" * 64

    def emit(self, record):
        try:
            msg = self.format(record)
            payload = (self._prev_hash + msg).encode("utf-8")
            current_hash = hashlib.sha256(payload).hexdigest()
            msg_with_chain = f"{msg} | prev_hash: {self._prev_hash[:16]}... | chain_hash: {current_hash}"
            self._prev_hash = current_hash
            self.stream.write(msg_with_chain + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)


class ForensicLogger:
    def __init__(self, log_file: str):
        self.log_file = log_file
        self.logger = logging.getLogger("wechat_forensic.Forensic")
        self.logger.setLevel(logging.INFO)

        # 避免重复添加处理器; 同时不要污染 root logger
        if self.logger.handlers:
            self.logger.handlers.clear()

        formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")

        file_handler = _ForensicFileHandler(log_file)
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
